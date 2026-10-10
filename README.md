# Previsao-Mega-Sena

Raio-X do Volante

Painel estatístico da Mega-Sena e da Quina com todos os sorteios da história: quantas vezes cada dezena saiu, há quanto tempo cada uma não aparece e o que o histórico diz sobre dezenas "quentes" e "frias", sempre com o teste estatístico ao lado de cada número.

Aviso: os sorteios são independentes. Nenhum método deste repositório aumenta a chance de ganhar; o próprio painel testa cada método contra o passado e mostra o resultado ao lado do que se espera do puro acaso.

Arquivos
Arquivo	O que é
painel.html	A página do painel, com os resultados e a projeção já gravados dentro dela.
atualizar_artifact.py	Acrescenta concursos novos à página e extrai o projecao.py embutido nela.
projecao.py	Refaz a "fórmula campeã" (projeção em Python) e grava a resposta na página.
O que o painel mostra
Estatísticas: frequência e atraso de cada dezena, teste do sorteio justo, pares e ímpares, soma das dezenas, duplas e trios mais sorteados.
Palpites: os métodos de escolha ordenados pelo desempenho no teste com o passado.
Projeções: fórmulas aplicadas aos 6 últimos concursos e a projeção em Python.
Gerador de jogos: jogos por estilo, com filtros opcionais de soma, pares, sequências e dezenas altas.
Conferidor: confere um jogo contra todos os sorteios já realizados.
Métodos de previsão: cada método comparado com a faixa em que cai quem joga ao acaso.
Como usar

Abra painel.html no navegador. A página funciona sozinha; só as fontes vêm da internet (Google Fonts).

Como atualizar com sorteios novos

Requisitos: Python 3 e numpy (pip install numpy).

Veja até onde a página vai:
bash
   python3 atualizar_artifact.py painel.html

O script mostra o último concurso gravado de cada loteria, grava painel_atualizado.html e extrai projecao.py.

Acrescente os concursos novos, em ordem crescente (uma loteria sem novidade pode ser omitida):
bash
   python3 atualizar_artifact.py painel.html \
     megasena 3068 08/10/2026 07,10,39,40,43,57 \
     quina 7138 08/10/2026 14,16,27,34,52

O script valida o número seguido, a data e as dezenas, e para com erro se algo não bater.

Refaça a projeção em Python (costuma levar de 2 a 5 minutos):
bash
   python3 projecao.py painel_atualizado.html

Ele só recalcula a loteria que ganhou concurso novo e termina com PY: recalculado e gravado ou PY: nada a recalcular.

Substitua painel.html pelo painel_atualizado.html.
Dados

Os resultados vêm da API oficial das Loterias Caixa (https://servicebus2.caixa.gov.br/portaldeloterias/api/<loteria>/<numero>), com os concursos antigos conferidos contra o espelho público guilhermeasn/loteria.json.

Situação atual: Mega-Sena até o concurso 3068 e Quina até o 7138, ambos de 08/10/2026.
