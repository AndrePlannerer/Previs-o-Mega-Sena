#!/usr/bin/env python3
import json, re, sys, datetime

pag = sys.argv[1]
html = open(pag, encoding="utf-8").read()
i = html.find("<title>"); assert i >= 0, "título não encontrado"
html = html[i:]
if html.rstrip().endswith("</body></html>"): html = html.rstrip()[:-len("</body></html>")].rstrip() + "\n"
m = re.search(r"const RAW = (\{.*?\});\nconst BT = ", html, re.S)
assert m, "linha RAW não encontrada"
raw = json.loads(m.group(1))
def estado(mod):
    L = raw[mod]; w = 8 + 2 * L["k"]; s = L["s"]; assert len(s) % w == 0
    n = len(s) // w; ult = s[(n - 1) * w:]
    return n, ult[:8], [int(ult[8 + 2 * j:10 + 2 * j]) for j in range(L["k"])], w
for mod in raw:
    n, d, z, _ = estado(mod); print(f"{mod}: último nº {n} em {d[6:8]}/{d[4:6]}/{d[:4]} {z}")
args = sys.argv[2:]
novos = []
i = 0
while i < len(args):
    mod, num, data, dz = args[i], int(args[i + 1]), args[i + 2], sorted(int(x) for x in args[i + 3].split(","))
    L = raw[mod]; n, dprev, _, w = estado(mod)
    assert num == n + 1, f"{mod}: esperado nº {n + 1}, veio {num}"
    dd, mm, aa = data.split("/"); iso = f"{aa}{mm}{dd}"; datetime.date(int(aa), int(mm), int(dd))
    assert iso >= dprev, f"{mod} {num}: data {data} anterior ao concurso anterior"
    assert len(dz) == L["k"] and len(set(dz)) == L["k"] and dz[0] >= 1 and dz[-1] <= L["N"], f"{mod} {num}: dezenas inválidas {dz}"
    L["s"] += iso + "".join(f"{x:02d}" for x in dz)
    novos.append(f"{mod} {num} {data} {dz}")
    i += 4
novo = html[:m.start(1)] + json.dumps(raw, separators=(",", ":")) + html[m.end(1):] if novos else html
assert novo[:m.start(1)] == html[:m.start(1)] and novo.endswith(html[m.end(1):])
open("painel_atualizado.html", "w", encoding="utf-8").write(novo)
print("gravado painel_atualizado.html com:", "; ".join(novos) if novos else "nenhum concurso novo (cópia sem mudanças)")
src = re.search(r'<script type="text/x-python" id="py-src">\n(.*?)</script>', novo, re.S)
assert src, "programa Python não encontrado na página"
open("projecao.py", "w", encoding="utf-8").write(src.group(1))
print("gravado projecao.py")
