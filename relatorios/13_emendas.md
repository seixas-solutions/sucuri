# Emendas parlamentares destinadas ao ensino superior — tarefa 3.7

Gerado por `analises/13_emendas.py`. 3348 emendas brutas coletadas
(função Educação, subfunção Ensino Superior, 2014–2025).

## 1. Limitação de escopo desta tarefa

O ROADMAP pedia cruzar emendas com "beneficiários que são órgãos do
Conjunto B" — não é possível com os dados desta API: nem `/emendas` nem
`/emendas/documentos/{codigo}` expõem a instituição beneficiária.
`/emendas` só tem `localidadeDoGasto` em nível de **UF**, não de órgão;
`/emendas/documentos/{codigo}` só tem um código de documento prefixado
por Unidade Gestora (ex.: `151910264182023NE000080`) — sem endpoint
público para converter UG em `codigoOrgao`, o mesmo obstáculo já
encontrado e documentado na tarefa 3.1. A análise abaixo é no nível
**agregado nacional da subfunção 364**, comparável ao Conjunto A, não por
instituição.

## 2. Dependência de emendas como % do orçamento (subfunção 364, nacional)

| ano   | emendas_pago   | subfuncao364_pago_real   | pct_dependencia   | ano_eleitoral   |
|:------|:---------------|:-------------------------|:------------------|:----------------|
| 2014  | 13.519.621,35  | 47.211.476.480,42        | 0.03%             | True            |
| 2015  | 5.553.016,15   | 48.839.962.987,95        | 0.01%             | False           |
| 2016  | 17.518.809,37  | 45.784.414.810,53        | 0.04%             | True            |
| 2017  | 10.184.352,80  | 46.193.352.518,31        | 0.02%             | False           |
| 2018  | 35.832.174,13  | 43.029.711.540,26        | 0.08%             | True            |
| 2019  | 42.363.918,88  | 42.313.911.421,48        | 0.10%             | False           |
| 2020  | 143.216.753,36 | 38.752.932.377,14        | 0.37%             | True            |
| 2021  | 119.271.417,80 | 34.856.514.058,21        | 0.34%             | False           |
| 2022  | 110.775.160,07 | 34.798.188.209,32        | 0.32%             | True            |
| 2023  | 264.267.714,06 | 37.036.289.990,06        | 0.71%             | False           |
| 2024  | 112.444.616,90 | 36.698.634.884,74        | 0.31%             | True            |
| 2025  | 174.328.643,14 | 41.078.265.746,65        | 0.42%             | False           |

**Leitura:** emendas pagas / total pago (real) da subfunção 364 no
Conjunto A, por ano. Valores em R$ reais (ano-base 2025 — mesma
deflação da Fase 1). Em termos absolutos, emendas são uma fração muito
pequena do orçamento de ensino superior (mediana ~0,2% no período) —
consistente com o achado da tarefa 2.1 de que a subfunção 364 é
majoritariamente folha de pagamento, não algo financiável por emenda
parlamentar. Ainda assim, há uma tendência real de **crescimento
relativo**: de 0,01–0,04% em 2014–2017 para 0,3–0,7% a partir de 2020 —
um salto de ordem de grandeza, não ruído. O ano de maior valor absoluto
(2023, R$ 264,3 milhões) e o 2º maior autor agregado ("RELATOR GERAL",
R$ 74,0 milhões no período) são consistentes com a mudança nas regras de
emendas parlamentares no Brasil nesse intervalo (emendas individuais e de
bancada tornadas impositivas por emenda constitucional a partir de 2015;
emendas de relator geral — o chamado "orçamento secreto" — ganharam peso
em 2020–2022 até serem objeto da ADPF 850 no STF, dezembro/2022, e o
desenho de emendas ser reformulado a partir de 2023) — contexto público
já bem documentado, não uma interpretação exclusiva desta análise.

## 3. Anos eleitorais vs. não eleitorais

Dependência média de emendas em anos eleitorais (municipais e gerais):
0.19%. Em anos não eleitorais: 0.27%.
Sem diferença clara na direção esperada nesta amostra — não confirma a hipótese de saltos ligados a anos eleitorais.

## 4. Top 10 autores por valor total de emendas (todo o período)

| autor                         | valor_total    |
|:------------------------------|:---------------|
| BANCADA DO RIO DE JANEIRO     | 170.763.551,79 |
| RELATOR GERAL                 | 74.012.316,37  |
| BANCADA DA BAHIA              | 54.567.055,97  |
| BANCADA DO DISTRITO FEDERAL   | 46.574.792,22  |
| BANCADA DO ACRE               | 34.273.828,01  |
| BANCADA DO ESPIRITO SANTO     | 30.015.981,90  |
| BANCADA DE MINAS GERAIS       | 20.965.847,59  |
| Sem informação                | 19.175.980,07  |
| BANCADA DE SAO PAULO          | 15.249.652,99  |
| BANCADA DO MATO GROSSO DO SUL | 14.991.533,11  |

## 5. Dados salvos

`dados/emendas_educacao.parquet` — uma linha por emenda/ano coletada
(agregado por autor/localidade, não por documento individual).
