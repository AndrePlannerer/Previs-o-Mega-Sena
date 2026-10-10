#!/usr/bin/env python3
# Projecao "formula campea" do Raio-X do Volante.
#
# Uso:  python3 projecao.py PAGINA.html
# Le os resultados gravados na pagina, refaz a conta e grava a resposta na linha "const PY = ...;".
#
# O que o programa faz, para cada loteria e cada alvo de acertos:
#   1. Testa formulas, uma por tentativa (a tentativa numero i e sempre a mesma formula):
#        dezena da posicao j = ((a*y3 + b*y2 + c*y1 + e_j) mod N) + 1
#      y3, y2, y1 = dezenas da mesma posicao nos tres concursos anteriores (y3 e o mais recente).
#      Se a dezena repetir uma posicao anterior do mesmo jogo, anda para a proxima dezena livre.
#   2. Guarda todas as que acertam o ultimo concurso (pelo menos "alvo" dezenas) dentro do orcamento
#      de tentativas. Se nenhuma acertar no orcamento, continua ate a primeira que acertar.
#   3. Aplica cada uma delas a todos os outros concursos da historia e fica com a CAMPEA:
#      a que mais acertou (empate: a de menor numero de tentativa).
#   4. Usa a campea com os tres concursos mais recentes para projetar o proximo.
import json, re, sys, time, datetime
import numpy as np

U = np.uint32
LOTERIAS = {"megasena": (60, 6), "quina": (80, 5)}
# orcamento de tentativas por alvo: (alvo mais facil, do meio, todas as dezenas)
ORCAMENTO = (1 << 22, 1 << 26, 1 << 30)
BLOCO = 1 << 20
LIMITE = (1 << 32) - 1


def wang(h):
    """Embaralhador de 32 bits (hash de Wang). h: vetor uint32."""
    h = (h ^ U(61)) ^ (h >> U(16))
    h = h + (h << U(3))
    h = h ^ (h >> U(4))
    h = h * U(0x27D4EB2D)
    h = h ^ (h >> U(15))
    return h


def parametros(i, N, k):
    """Multiplicadores a, b, c e constantes e_1..e_k (0 a N-1) da tentativa i."""
    n = U(N)
    h, h2, h3 = wang(i), wang(i + U(0x9E3779B9)), wang(i + U(0x7F4A7C15))
    a, b, c = h % n, (h // n) % n, (h // (n * n)) % n
    e = [h2 % n, (h2 // n) % n, (h2 // (n * n)) % n, (h2 // (n * n * n)) % n, h3 % n, (h3 // n) % n][:k]
    return a, b, c, e


def montar(a, b, c, e, y1, y2, y3, N, feitas=()):
    """Dezenas de uma posicao: aplica a formula e, se a dezena ja saiu numa posicao anterior do mesmo
    jogo (`feitas`), anda para a proxima dezena livre (depois de N volta para 1)."""
    v = (a * y3 + b * y2 + c * y1 + e) % U(N) + U(1)
    for _ in feitas:
        rep = v == feitas[0]
        for f in feitas[1:]:
            rep = rep | (v == f)
        if not rep.any():
            break
        v = np.where(rep, v % U(N) + U(1), v)
    return v


def jogos(i, Y, N):
    """Jogos das tentativas i a partir de Y (3 concursos: antigo, meio, recente). Matriz len(i) x k."""
    k = Y.shape[1]
    a, b, c, e = parametros(i, N, k)
    y = Y.astype(U)
    cols = []
    for j in range(k):
        cols.append(montar(a, b, c, e[j], y[0, j], y[1, j], y[2, j], N, cols))
    return np.stack(cols, 1)


def candidatas(Y, real, N, alvo, ini, fim):
    """Tentativas em [ini, fim) cujo jogo acerta pelo menos `alvo` dezenas de `real`."""
    k = Y.shape[1]
    marca = np.zeros(N + 2, dtype=np.int8)
    marca[real] = 1
    y = Y.astype(U)
    achadas = []
    for p in range(ini, fim, BLOCO):
        i = np.arange(p, min(p + BLOCO, fim), dtype=np.uint64).astype(U)
        n = U(N)
        h, h2, h3 = wang(i), wang(i + U(0x9E3779B9)), None  # mesmos parametros de parametros(), calculados so quando precisa
        a, b, c = h % n, (h // n) % n, (h // (n * n)) % n
        erros = np.zeros(len(i), dtype=np.int8)
        cols = []
        for j in range(k):  # descarta cedo quem ja errou demais
            if j < 4:
                e = (h2 // U(N ** j)) % n
            else:
                if h3 is None:
                    h3 = wang(i + U(0x7F4A7C15))
                e = (h3 // U(N ** (j - 4))) % n
            v = montar(a, b, c, e, y[0, j], y[1, j], y[2, j], N, cols)
            erros = erros + (1 - marca[v])
            cols.append(v)
            if j >= k - alvo:
                fica = erros <= k - alvo
                if not fica.all():
                    i, a, b, c, erros, h2 = i[fica], a[fica], b[fica], c[fica], erros[fica], h2[fica]
                    h3 = None if h3 is None else h3[fica]
                    cols = [x[fica] for x in cols]
                if not len(i):
                    break
        if len(i):
            achadas.append(i)
    return np.concatenate(achadas) if achadas else np.zeros(0, dtype=U)


def acertos_na_historia(i, D, N, ate):
    """Total de acertos de cada tentativa i nos concursos de indice 3..ate-1 (cada um previsto pelos 3 anteriores)."""
    k = D.shape[1]
    T = np.arange(3, ate)
    Y1, Y2, Y3, R = D[T - 3].astype(U), D[T - 2].astype(U), D[T - 1].astype(U), D[T].astype(U)
    tot = np.zeros(len(i), dtype=np.int64)
    passo = max(1, 2_000_000 // max(1, len(T)))
    for s in range(0, len(i), passo):
        a, b, c, e = [x[:, None] if not isinstance(x, list) else [z[:, None] for z in x] for x in parametros(i[s:s + passo], N, k)]
        V = []
        for j in range(k):
            V.append(montar(a, b, c, e[j], Y1[None, :, j], Y2[None, :, j], Y3[None, :, j], N, V))
        for q in range(k):
            bateu = V[0] == R[None, :, q]
            for j in range(1, k):
                bateu |= V[j] == R[None, :, q]
            tot[s:s + passo] += bateu.sum(1)
    return tot, len(T)


def campea(D, N, alvo, orcamento):
    """Devolve o resumo da formula campea para o ultimo concurso de D."""
    n, k = D.shape
    Y, real, Yproj = D[n - 4:n - 1], D[n - 1], D[n - 3:n]
    cand = candidatas(Y, real, N, alvo, 1, orcamento + 1)
    examinadas = orcamento
    p = orcamento + 1
    while not len(cand) and p < LIMITE:  # nada no orcamento: segue ate a primeira que acertar
        fim = min(p + (1 << 24), LIMITE)
        cand = candidatas(Y, real, N, alvo, p, fim)[:1]
        examinadas = int(cand[0]) if len(cand) else fim - 1
        p = fim
    tot, m = acertos_na_historia(cand, D, N, n - 1)
    w = int(np.argmax(tot))  # empate: a primeira (menor tentativa)
    i = cand[w:w + 1]
    a, b, c, e = parametros(i, N, k)
    previsto = jogos(i, Y, N)[0].tolist()
    return {
        "alvo": alvo, "tentativa": int(i[0]), "a": int(a[0]), "b": int(b[0]), "c": int(c[0]), "e": [int(x[0]) for x in e],
        "previsto": previsto, "acertos": len(set(previsto) & set(real.tolist())),
        "projecao": jogos(i, Yproj, N)[0].tolist(),
        "outros": m, "outros_media": round(float(tot[w]) / m, 4),
        "examinadas": examinadas, "candidatas": int(len(cand)),
        "candidatas_media": round(float(tot.mean()) / m, 4),
        "primeira": {"tentativa": int(cand[0]), "outros_media": round(float(tot[0]) / m, 4)},
    }


def ler_resultados(raw, mod):
    L = raw[mod]
    k, s = L["k"], L["s"]
    w = 8 + 2 * k
    assert len(s) % w == 0
    return np.array([[int(s[t + 8 + 2 * j:t + 10 + 2 * j]) for j in range(k)] for t in range(0, len(s), w)], dtype=np.int64)


def calcular(raw, antigo=None, log=print):
    out = {}
    for mod, (N, k) in LOTERIAS.items():
        D = np.sort(ler_resultados(raw, mod), 1)
        n = len(D)
        if antigo and antigo.get(mod, {}).get("n") == n:
            out[mod] = antigo[mod]
            log(f"{mod}: ja estava em dia (concurso {n})")
            continue
        res = {}
        for alvo, orc in zip((k - 2, k - 1, k), ORCAMENTO):
            t0 = time.time()
            r = campea(D, N, alvo, orc)
            res[str(alvo)] = r
            log(f"{mod} alvo {alvo}: campea = tentativa {r['tentativa']} entre {r['candidatas']} candidatas, "
                f"media na historia {r['outros_media']}, projecao {sorted(r['projecao'])} ({time.time() - t0:.0f}s)")
        out[mod] = {"n": n, "res": res}
    return out


if __name__ == "__main__":
    pagina = sys.argv[1]
    html = open(pagina, encoding="utf-8").read()
    m_raw = re.search(r"const RAW = (\{.*?\});\nconst BT = ", html, re.S)
    m_py = re.search(r"^const PY = (.*);$", html, re.M)
    assert m_raw and m_py, "linhas RAW/PY nao encontradas"
    raw, antigo = json.loads(m_raw.group(1)), json.loads(m_py.group(1))
    novo = calcular(raw, antigo)
    if novo == {q: antigo.get(q) for q in novo}:
        print("PY: nada a recalcular")
        sys.exit(0)
    novo["gerado"] = datetime.date.today().isoformat()
    saida = html[:m_py.start(1)] + json.dumps(novo, separators=(",", ":")) + html[m_py.end(1):]
    open(pagina, "w", encoding="utf-8").write(saida)
    print("PY: recalculado e gravado em", pagina)
