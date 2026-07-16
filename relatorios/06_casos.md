# Consolidação e priorização de casos — tarefa 2.5

Gerado por `analises/06_casos.py`. Unifica sinais das tarefas 2.1–2.4:
flag_anomalia (Fase 1), score de outliers multivariados (2.3, Isolation
Forest + LOF) e desvio de tendência robusta (2.4, Theil–Sen — só Conjunto
B). A Lei de Benford (2.2) não entra aqui: é um teste de conformidade do
**conjunto/grupo** como um todo, não produz um sinal por entidade/ano (ver
`relatorios/03_benford.md`). **Ano parcial excluído de toda a análise desta
tarefa.**

`score_combinado` = média dos sinais disponíveis para a linha, cada um em
[0, 1] (1 = mais anômalo): `flag_anomalia` (binário: 0 ou 1),
`score_anomalia` de 2.3, e — só para o Conjunto B — o rank percentual do
desvio de 2.4 entre os eventos detectados. Só entram na tabela linhas em
que pelo menos um sinal **disparou** de fato: `flag_anomalia=True`, ou
`score_anomalia` no top 10% do seu grupo (2.3), ou presença em
`eventos_series.csv` (2.4). `score_anomalia` isolado sendo positivo não
basta — é um rank contínuo quase sempre > 0 para qualquer linha elegível,
não um indicador de disparo.

Casos candidatos totais: 176 (29 no Conjunto A,
147 no Conjunto B). 155 casos têm 2 ou mais
sinais concordando — esses merecem prioridade adicional na checagem
manual, por triangulação de métodos independentes.

## Top 15 casos priorizados

**1. Fundação Universidade Federal do Acre — 2025** (Conjunto B, R$ 496.21 milhões reais, score 0.93)
   Sinais: zscore_robusto, outlier_multivariado(score=0.95), tendencia_robusta(desvio=4.0). Score combinado: 0.93 (de 3 sinal(is)).

**2. Instituto Federal de Educação, Ciência e Tecn — 2025** (Conjunto B, R$ 428.39 milhões reais, score 0.92)
   Sinais: zscore_robusto, outlier_multivariado(score=0.87), tendencia_robusta(desvio=4.2). Score combinado: 0.92 (de 3 sinal(is)).

**3. Universidade Federal do Oeste da Bahia — 2015** (Conjunto B, R$ 49.27 milhões reais, score 0.92)
   Padrão já identificado: universidade da expansão federal 2013–2014 — orçamento de implantação baixo no(s) primeiro(s) ano(s), não evento atípico (ver relatorios/02_eda.md, seção 6). Sinais: zscore_robusto, salto_anual, outlier_multivariado(score=1.00), tendencia_robusta(desvio=-3.5). Score combinado: 0.92 (de 3 sinal(is)).

**4. Instituto Federal de Educação, Ciência e Tecn — 2025** (Conjunto B, R$ 941.69 milhões reais, score 0.82)
   Sinais: zscore_robusto, outlier_multivariado(score=0.97), tendencia_robusta(desvio=2.9). Score combinado: 0.82 (de 3 sinal(is)).

**5. Universidade Federal da Integração Latino-Ame — 2025** (Conjunto B, R$ 288.82 milhões reais, score 0.76)
   Sinais: zscore_robusto, outlier_multivariado(score=0.84), tendencia_robusta(desvio=2.9). Score combinado: 0.76 (de 3 sinal(is)).

**6. Fundação Universidade Federal do Vale do São  — 2025** (Conjunto B, R$ 352.50 milhões reais, score 0.72)
   Sinais: zscore_robusto, outlier_multivariado(score=0.19), tendencia_robusta(desvio=7.8). Score combinado: 0.72 (de 3 sinal(is)).

**7. Universidade Federal Rural do Rio de Janeiro — 2021** (Conjunto B, R$ 736.75 milhões reais, score 0.52)
   Sinais: outlier_multivariado(score=0.62), tendencia_robusta(desvio=-4.2). Score combinado: 0.51 (de 3 sinal(is)).

**8. Universidade Federal de Ouro Preto — 2025** (Conjunto B, R$ 590.26 milhões reais, score 0.50)
   Sinais: outlier_multivariado(score=0.79), tendencia_robusta(desvio=3.3). Score combinado: 0.50 (de 3 sinal(is)).

**9. Universidade Federal de Campina Grande — 2025** (Conjunto B, R$ 955.48 milhões reais, score 0.42)
   Sinais: outlier_multivariado(score=0.89), tendencia_robusta(desvio=2.8). Score combinado: 0.42 (de 3 sinal(is)).

**10. Universidade Federal Rural do Rio de Janeiro — 2022** (Conjunto B, R$ 736.39 milhões reais, score 0.42)
   Sinais: outlier_multivariado(score=0.48), tendencia_robusta(desvio=-3.8). Score combinado: 0.42 (de 3 sinal(is)).

**11. Fundação Universidade de Brasília — 2025** (Conjunto B, R$ 2,399.44 milhões reais, score 0.40)
   Sinais: outlier_multivariado(score=0.80), tendencia_robusta(desvio=2.8). Score combinado: 0.40 (de 3 sinal(is)).

**12. Universidade Federal do Rio Grande do Norte — 2017** (Conjunto B, R$ 2,569.02 milhões reais, score 0.40)
   Sinais: outlier_multivariado(score=0.97), tendencia_robusta(desvio=2.7). Score combinado: 0.40 (de 3 sinal(is)).

**13. Fundação Universidade do Maranhão — 2025** (Conjunto B, R$ 1,202.29 milhões reais, score 0.40)
   Sinais: outlier_multivariado(score=0.46), tendencia_robusta(desvio=3.3). Score combinado: 0.40 (de 3 sinal(is)).

**14. Hospital de Clínicas de Porto Alegre — 2017** (Conjunto B, R$ 2,114.57 milhões reais, score 0.38)
   Sinais: outlier_multivariado(score=0.48), tendencia_robusta(desvio=3.1). Score combinado: 0.38 (de 3 sinal(is)).

**15. Fundação Universidade Federal do Vale do São  — 2024** (Conjunto B, R$ 315.84 milhões reais, score 0.36)
   Sinais: outlier_multivariado(score=0.20), tendencia_robusta(desvio=4.2). Score combinado: 0.36 (de 3 sinal(is)).

## Tabela completa (top 15)

| conjunto   | entidade_curta                                |   ano |   pago_real_mi |   score_combinado |   n_sinais | sinais                                                                                        |
|:-----------|:----------------------------------------------|------:|---------------:|------------------:|-----------:|:----------------------------------------------------------------------------------------------|
| B          | Fundação Universidade Federal do Acre         |  2025 |         496.21 |             0.926 |          3 | zscore_robusto, outlier_multivariado(score=0.95), tendencia_robusta(desvio=4.0)               |
| B          | Instituto Federal de Educação, Ciência e Tecn |  2025 |         428.39 |             0.923 |          3 | zscore_robusto, outlier_multivariado(score=0.87), tendencia_robusta(desvio=4.2)               |
| B          | Universidade Federal do Oeste da Bahia        |  2015 |          49.27 |             0.916 |          3 | zscore_robusto, salto_anual, outlier_multivariado(score=1.00), tendencia_robusta(desvio=-3.5) |
| B          | Instituto Federal de Educação, Ciência e Tecn |  2025 |         941.69 |             0.822 |          3 | zscore_robusto, outlier_multivariado(score=0.97), tendencia_robusta(desvio=2.9)               |
| B          | Universidade Federal da Integração Latino-Ame |  2025 |         288.82 |             0.763 |          3 | zscore_robusto, outlier_multivariado(score=0.84), tendencia_robusta(desvio=2.9)               |
| B          | Fundação Universidade Federal do Vale do São  |  2025 |         352.5  |             0.722 |          3 | zscore_robusto, outlier_multivariado(score=0.19), tendencia_robusta(desvio=7.8)               |
| B          | Universidade Federal Rural do Rio de Janeiro  |  2021 |         736.75 |             0.515 |          3 | outlier_multivariado(score=0.62), tendencia_robusta(desvio=-4.2)                              |
| B          | Universidade Federal de Ouro Preto            |  2025 |         590.26 |             0.497 |          3 | outlier_multivariado(score=0.79), tendencia_robusta(desvio=3.3)                               |
| B          | Universidade Federal de Campina Grande        |  2025 |         955.48 |             0.42  |          3 | outlier_multivariado(score=0.89), tendencia_robusta(desvio=2.8)                               |
| B          | Universidade Federal Rural do Rio de Janeiro  |  2022 |         736.39 |             0.418 |          3 | outlier_multivariado(score=0.48), tendencia_robusta(desvio=-3.8)                              |
| B          | Fundação Universidade de Brasília             |  2025 |        2399.44 |             0.398 |          3 | outlier_multivariado(score=0.80), tendencia_robusta(desvio=2.8)                               |
| B          | Universidade Federal do Rio Grande do Norte   |  2017 |        2569.02 |             0.398 |          3 | outlier_multivariado(score=0.97), tendencia_robusta(desvio=2.7)                               |
| B          | Fundação Universidade do Maranhão             |  2025 |        1202.29 |             0.395 |          3 | outlier_multivariado(score=0.46), tendencia_robusta(desvio=3.3)                               |
| B          | Hospital de Clínicas de Porto Alegre          |  2017 |        2114.57 |             0.375 |          3 | outlier_multivariado(score=0.48), tendencia_robusta(desvio=3.1)                               |
| B          | Fundação Universidade Federal do Vale do São  |  2024 |         315.84 |             0.36  |          3 | outlier_multivariado(score=0.20), tendencia_robusta(desvio=4.2)                               |

## Leitura geral

Esta lista prioriza checagem manual e cruzamento com fontes externas (Fase
3 do ROADMAP: contratos, licitações, sanções, convênios) — **não é uma
lista de irregularidades**. Casos marcados com nota de "padrão já
identificado" têm explicação estrutural razoável encontrada nas próprias
tarefas 2.1–2.4 (universidades novas em rampa de implantação, ação
genérica de folha de pagamento, dominância de escala) e devem ser
priorizados por último dentro desta lista, mesmo com score alto — o score
combinado não sabe distinguir "estatisticamente extremo" de "já explicado
por contexto conhecido"; essa distinção só existe porque as tarefas
anteriores investigaram manualmente cada padrão recorrente. Os casos sem
nota não têm explicação estrutural encontrada até aqui e são a prioridade
real de investigação desta fase.

**Achado adicional desta consolidação, não visível em nenhuma tarefa
anterior isoladamente:** 2025 responde por 35 dos 176 casos
(20%, bem acima dos ~8% esperados se os casos se distribuíssem
igualmente entre os 12 anos completos) e por 16 dos
33 casos com o número máximo de sinais concordantes — quase
metade da camada de maior confiança. Isso é consistente com o achado da
tarefa 2.1 (`relatorios/02_eda.md`, seção 1) de que 2025 é o novo máximo
real da série tanto no Conjunto A quanto no B, após a recuperação pós-2021.
**Leitura recomendada:** boa parte dos casos de 2025 provavelmente não são
35 eventos independentes, e sim a mesma tendência macro de
recuperação/crescimento real do orçamento do MEC se manifestando
instituição por instituição — cada modelo de tendência (Theil–Sen) vê
apenas sua própria série e não tem como saber que o aumento é generalizado.
Isso não invalida os casos individuais (o aumento pode ainda ser
desproporcional em alguns deles), mas muda a pergunta de "por que esta
instituição teve um salto" para "esta instituição cresceu mais que a média
do setor em 2025, e por quê" — uma investigação comparativa, não isolada.
