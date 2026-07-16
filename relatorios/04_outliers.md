# Modelos não supervisionados de detecção de outliers — tarefa 2.3

Gerado por `analises/04_outliers.py`. Isolation Forest e Local Outlier
Factor (LOF) sobre features padronizadas: `pago_real`, `taxa_liquidacao`, `taxa_pagamento`, `variacao_pago_aa`, `restos_a_pagar_frac`.
Score combinado (`score_anomalia`) = média dos ranks normalizados dos dois
métodos (0 a 1, 1 = mais anômalo). `rank_anomalia` = posição no ranking
combinado (1 = mais anômalo).

## 1. Conjunto A

Linhas totais: 1249. Linhas elegíveis (sem NaN nas
features — exclui ano parcial e séries curtas, já tratados na Fase 1):
118.

### Top 20 por `score_anomalia`

| programa                                                                  | acao                                                                                             |   ano |   score_anomalia |   rank_anomalia |   rank_isolation_forest |   rank_lof |   pago_real_mi |
|:--------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------|------:|-----------------:|----------------:|------------------------:|-----------:|---------------:|
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | RECONSTRUCAO E MODERNIZACAO DO MUSEU NACIONAL                                                    |  2022 |         1        |               1 |                       1 |          1 |           3.8  |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | IMPLANTACAO DA UNIVERSIDADE FEDERAL DA FRONTEIRA SUL - UFFS                                      |  2015 |         0.982906 |               2 |                       3 |          3 |          14.09 |
| PROGRAMA DE GESTAO E MANUTENCAO DO MINISTERIO DA EDUCACAO                 | ATIVOS CIVIS DA UNIAO                                                                            |  2017 |         0.978632 |               3 |                       5 |          2 |       32869.7  |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | APOIO A CONSOLIDACAO, REESTRUTURACAO E MODERNIZACAO DAS INSTITUICOES FEDERAIS DE ENSINO SUPERIOR |  2022 |         0.974359 |               4 |                       2 |          6 |          21.73 |
| PROGRAMA DE GESTAO E MANUTENCAO DO MINISTERIO DA EDUCACAO                 | ATIVOS CIVIS DA UNIAO                                                                            |  2015 |         0.961538 |               5 |                       6 |          5 |       29250.4  |
| PROGRAMA DE GESTAO E MANUTENCAO DO MINISTERIO DA EDUCACAO                 | ATIVOS CIVIS DA UNIAO                                                                            |  2016 |         0.961538 |               6 |                       7 |          4 |       29937.8  |
| PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO                        | ATIVOS CIVIS DA UNIAO                                                                            |  2025 |         0.948718 |               7 |                       4 |         10 |       29084.4  |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | APOIO AO FUNCIONAMENTO DAS INSTITUICOES FEDERAIS DE EDUCACAO SUPERIOR                            |  2022 |         0.923077 |               8 |                      11 |          9 |          18.51 |
| PROGRAMA DE GESTAO E MANUTENCAO DO MINISTERIO DA EDUCACAO                 | ATIVOS CIVIS DA UNIAO                                                                            |  2018 |         0.918803 |               9 |                      13 |          8 |       30160    |
| PROGRAMA DE GESTAO E MANUTENCAO DO MINISTERIO DA EDUCACAO                 | ATIVOS CIVIS DA UNIAO                                                                            |  2019 |         0.918803 |              10 |                      14 |          7 |       30272.3  |
| PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO                        | ATIVOS CIVIS DA UNIAO                                                                            |  2023 |         0.91453  |              11 |                       9 |         13 |       25744.4  |
| PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO                        | ATIVOS CIVIS DA UNIAO                                                                            |  2022 |         0.91453  |              11 |                      10 |         12 |       25903.2  |
| PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO                        | ATIVOS CIVIS DA UNIAO                                                                            |  2024 |         0.91453  |              13 |                       8 |         14 |       25613.5  |
| PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO                        | ATIVOS CIVIS DA UNIAO                                                                            |  2021 |         0.888889 |              14 |                      17 |         11 |       26937.3  |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | CONCESSAO DE BOLSAS DE ESTUDO NO ENSINO SUPERIOR                                                 |  2015 |         0.880342 |              15 |                      15 |         15 |        9925.97 |
| EDUCACAO DE QUALIDADE PARA TODOS                                          | AMPLIACAO E REESTRUTURACAO DE INSTITUICOES MILITARES DE ENSINO SUPERIOR                          |  2018 |         0.858974 |              16 |                      12 |         23 |           0    |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | APOIO A CONSOLIDACAO, REESTRUTURACAO E MODERNIZACAO DAS INSTITUICOES FEDERAIS DE ENSINO SUPERIOR |  2021 |         0.837607 |              17 |                      16 |         24 |           0.3  |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | RECONSTRUCAO E MODERNIZACAO DO MUSEU NACIONAL                                                    |  2021 |         0.820513 |              18 |                      19 |         25 |           0.02 |
| EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | REESTRUTURACAO E MODERNIZACAO DAS INSTITUICOES FEDERAIS DE ENSINO SUPERIOR                       |  2015 |         0.816239 |              19 |                      26 |         19 |        1844.97 |
| ESTATISTICAS E AVALIACOES EDUCACIONAIS                                    | CENSO DA EDUCACAO SUPERIOR                                                                       |  2022 |         0.811966 |              20 |                      20 |         26 |           0.31 |

### Concordância entre métodos (top 10% de cada)

Interseção: 9 de 12
linhas no top 10% de ambos os métodos (índice de Jaccard:
0.60).

### Concordância com `flag_anomalia` (Fase 1)

|                     |   top_10pct_score=False |   top_10pct_score=True |
|:--------------------|------------------------:|-----------------------:|
| flag_anomalia=False |                     100 |                     10 |
| flag_anomalia=True  |                       6 |                      2 |

## 2. Conjunto B (por tipo de instituição)

Linhas totais: 1484. Linhas elegíveis (agregando todos os
tipos processados): 1217. Grupos pulados por
amostra insuficiente (<20 linhas elegíveis): CAPES (n=11); Educação Básica (n=11); Fundo (FNDE/FIES) (n=11).

### Top 20 por `score_anomalia`

| orgao                                                                     | tipo_instituicao               |   ano |   score_anomalia |   rank_anomalia |   rank_isolation_forest |   rank_lof |   pago_real_mi |
|:--------------------------------------------------------------------------|:-------------------------------|------:|-----------------:|----------------:|------------------------:|-----------:|---------------:|
| Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira    | Outros / Administração         |  2020 |         1        |               1 |                       1 |          1 |         554.17 |
| Empresa Brasileira de Serviços Hospitalares                               | Hospitalar (EBSERH)            |  2015 |         1        |               1 |                       1 |          1 |        3070.45 |
| Universidade Federal do Sul da Bahia                                      | Universidade Federal           |  2015 |         0.998613 |               3 |                       7 |          1 |          56.9  |
| Universidade Federal do Norte do Tocantins                                | Universidade Federal           |  2023 |         0.998613 |               3 |                       5 |          5 |          33.51 |
| Universidade Federal do Oeste da Bahia                                    | Universidade Federal           |  2015 |         0.997226 |               5 |                       1 |         10 |          49.27 |
| Fundação Universidade Federal do Amapá                                    | Universidade Federal           |  2016 |         0.996533 |               6 |                       8 |          7 |         236.37 |
| Instituto Federal de Educação, Ciência e Tecnologia do Mato Grosso do Sul | Instituto/CEFET/Escola Técnica |  2017 |         0.995444 |               7 |                      14 |          1 |         254.88 |
| Instituto Federal de Educação, Ciência e Tecnologia de São Paulo          | Instituto/CEFET/Escola Técnica |  2025 |         0.995444 |               7 |                      11 |          6 |        1515.53 |
| Fundação Universidade Federal do Amapá                                    | Universidade Federal           |  2019 |         0.995146 |               9 |                      10 |          8 |         252.05 |
| Fundação Universidade Federal do Amapá                                    | Universidade Federal           |  2018 |         0.992372 |              10 |                      13 |         12 |         254.59 |
| Instituto Federal de Educação, Ciência e Tecnologia do Amapá              | Instituto/CEFET/Escola Técnica |  2025 |         0.992027 |              11 |                       9 |         17 |         154.84 |
| Instituto Federal de Educação, Ciência e Tecnologia do Amapá              | Instituto/CEFET/Escola Técnica |  2021 |         0.990888 |              12 |                       1 |         25 |         103.93 |
| Universidade Federal do Rio de Janeiro                                    | Universidade Federal           |  2017 |         0.990291 |              13 |                      15 |         15 |        5818.15 |
| Universidade Federal do Cariri                                            | Universidade Federal           |  2015 |         0.990291 |              13 |                      12 |         18 |          98.53 |
| Universidade Federal do Delta do Parnaíba                                 | Universidade Federal           |  2025 |         0.989598 |              15 |                      18 |         13 |         110.44 |
| Universidade Federal do Rio de Janeiro                                    | Universidade Federal           |  2016 |         0.988904 |              16 |                      16 |         16 |        5697.32 |
| Instituto Federal de Educação, Ciência e Tecnologia do Amapá              | Instituto/CEFET/Escola Técnica |  2020 |         0.98861  |              17 |                       6 |         27 |         114.26 |
| Instituto Federal de Educação, Ciência e Tecnologia de São Paulo          | Instituto/CEFET/Escola Técnica |  2016 |         0.987472 |              18 |                      25 |         11 |        1069.59 |
| Universidade Federal do Rio de Janeiro                                    | Universidade Federal           |  2015 |         0.985437 |              19 |                      20 |         21 |        5518.84 |
| Universidade Federal do Rio de Janeiro                                    | Universidade Federal           |  2025 |         0.984743 |              20 |                      23 |         20 |        4445.35 |

### Concordância entre métodos (top 10% de cada)

Interseção: 68 de 122
linhas no top 10% de ambos os métodos (índice de Jaccard:
0.39).

### Concordância com `flag_anomalia` (Fase 1)

|                     |   top_10pct_score=False |   top_10pct_score=True |
|:--------------------|------------------------:|-----------------------:|
| flag_anomalia=False |                    1086 |                     89 |
| flag_anomalia=True  |                       9 |                     33 |

## 3. Interpretação

Isolation Forest e LOF detectam tipos diferentes de desvio (isolamento
global vs. densidade local) — concordância parcial é esperada e não é um
defeito: interseção alta indica outliers "óbvios" (destacados nos dois
critérios); pontos capturados por só um método são candidatos mais sutis,
não devem ser descartados. A concordância com `flag_anomalia` mede se os
dois modelos multivariados redescobrem o que as regras univariadas da
Fase 1 já sinalizavam — sobreposição parcial (não total) é o resultado
esperado, já que os modelos usam informação adicional (nível do gasto,
taxas de execução) que as flags de série temporal isoladas não capturam.

Dois padrões no top 20 do Conjunto B já têm explicação estrutural
identificada nas tarefas anteriores, e não devem ser lidos como achados
novos:

- **Universidades federais recém-criadas** (Cariri, Sul da Bahia, Oeste da
  Bahia — 2015): mesmo padrão de rampa de implantação já discutido em
  `relatorios/02_eda.md`, seção 6 — orçamento do primeiro/segundo ano muito
  diferente do padrão maduro da própria instituição, mas coerente com a
  expansão federal de 2013–2014, não um evento atípico de gasto.
- **UFRJ aparece em 4 dos 20 primeiros lugares** (2015–2017, 2025): dentro
  do grupo `Universidade Federal` (791 linhas, todas as universidades
  federais juntas, sem subdivisão por porte), UFRJ está entre as maiores
  em valor absoluto — o modelo pode estar capturando principalmente
  **dominância de escala** (uma universidade grande destoa de centenas de
  universidades menores no mesmo grupo), não necessariamente comportamento
  atípico de execução orçamentária. Uma iteração futura poderia
  segmentar `Universidade Federal` por porte (matrículas/orçamento) antes
  de rodar os modelos, isolando esse efeito.

Os demais casos do top 20 (institutos federais de porte médio, Hospitalar/
EBSERH, INEP) não têm explicação estrutural evidente nos dados já
analisados e permanecem como prioridade de checagem manual — consolidados
com os demais sinais na tarefa 2.5.
