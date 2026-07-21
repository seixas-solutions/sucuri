# Cruzamento com o IBGE — população (tarefa 4.4)

Fonte IBGE: agregado 6579 (população residente estimada), variável 9324,
API pública de agregados (`analises/00b_baixar_ibge.py`). População de
2022–2023 **interpolada linearmente** (sem estimativa publicada) — linhas
marcadas em `interpolado`.

## 1. Despesa real per capita nacional (Conjunto A, subfunção 364)

Método: `pago_real` anual (R$ de 2025, ano parcial excluído) ÷
população do Brasil no ano.

|   ano |   pago_real_bi |   populacao_mi |   per_capita_real | interpolado   |
|------:|---------------:|---------------:|------------------:|:--------------|
|  2014 |          47.21 |          202.8 |            232.83 | False         |
|  2015 |          48.84 |          204.5 |            238.88 | False         |
|  2016 |          45.78 |          206.1 |            222.17 | False         |
|  2017 |          46.19 |          207.7 |            222.45 | False         |
|  2018 |          43.03 |          208.5 |            206.38 | False         |
|  2019 |          42.31 |          210.1 |            201.35 | False         |
|  2020 |          38.75 |          211.8 |            183.01 | False         |
|  2021 |          34.86 |          213.3 |            163.40 | False         |
|  2022 |          34.80 |          213.1 |            163.32 | True          |
|  2023 |          37.04 |          212.8 |            174.02 | True          |
|  2024 |          36.70 |          212.6 |            172.63 | False         |
|  2025 |          41.08 |          213.4 |            192.48 | False         |

- Pico per capita: **2015** (R$ 238,88); piso: **2022** (R$ 163,32).
- A trajetória em U da tarefa 2.1 persiste em termos per capita — o
  crescimento populacional (~5% no período) não explica a queda até 2021
  nem a recuperação posterior.

## 2. Emendas parlamentares per capita por UF (2014–2025 acumulado)

Método: `valorPago` deflacionado (IPCA, R$ de 2025) somado por UF
(UF extraída de `localidadeDoGasto` — `sucuri.ibge.extrair_uf`) ÷ população
média da UF no período; z-score robusto (0,6745·(x−mediana)/MAD) entre as
27 UFs, limiar |z| > 3.5.

- 148 de 3348 emendas (R$ 128.147.380,96, 10.4% do valor)
  não têm UF atribuível ("Nacional", regiões, "MÚLTIPLO") e ficam fora
  do rateio — ressalva, não descarte silencioso.

| sigla_uf   |   valor_pago_real_mi |   n_emendas |   per_capita_real |   zscore_robusto | flag_atipico   |
|:-----------|---------------------:|------------:|------------------:|-----------------:|:---------------|
| AC         |                41.86 |          53 |             48.55 |            14.28 | True           |
| RJ         |               453.65 |         602 |             26.59 |             7.30 | True           |
| DF         |                63.76 |          72 |             21.26 |             5.61 | True           |
| AP         |                17.18 |          97 |             21.04 |             5.54 | True           |
| ES         |                34.91 |          37 |              8.65 |             1.60 | False          |
| RN         |                29.03 |         127 |              8.33 |             1.50 | False          |
| MS         |                20.51 |          48 |              7.37 |             1.20 | False          |
| TO         |                10.03 |          59 |              6.41 |             0.89 | False          |
| RR         |                 3.46 |          35 |              5.67 |             0.66 | False          |
| SE         |                12.08 |          40 |              5.28 |             0.53 | False          |
| BA         |                77.55 |         182 |              5.17 |             0.50 | False          |
| PA         |                39.31 |         168 |              4.61 |             0.32 | False          |
| MG         |                78.12 |         302 |              3.69 |             0.03 | False          |
| MT         |                12.71 |          22 |              3.61 |             0.00 | False          |
| GO         |                19.91 |         102 |              2.84 |            -0.24 | False          |
| MA         |                18.67 |          66 |              2.66 |            -0.30 | False          |
| SC         |                16.75 |          83 |              2.29 |            -0.42 | False          |
| PR         |                20.40 |         204 |              1.78 |            -0.58 | False          |
| RS         |                20.05 |         172 |              1.77 |            -0.58 | False          |
| CE         |                14.85 |         101 |              1.63 |            -0.63 | False          |
| AL         |                 5.04 |          34 |              1.52 |            -0.66 | False          |
| AM         |                 6.15 |          51 |              1.48 |            -0.67 | False          |
| SP         |                65.27 |         232 |              1.43 |            -0.69 | False          |
| PB         |                 5.51 |          99 |              1.36 |            -0.71 | False          |
| RO         |                 2.29 |          21 |              1.29 |            -0.74 | False          |
| PE         |                10.80 |         145 |              1.14 |            -0.79 | False          |
| PI         |                 1.30 |          46 |              0.40 |            -1.02 | False          |

UFs atípicas (|z| acima do limiar): AC, RJ, DF, AP

**Leitura de atipicidade, não de irregularidade:** per capita alto em UFs
pequenas é esperado quando a emenda financia uma instituição federal que
atende além da própria UF; o indicador serve para orientar comparação
entre pares, não para concluir desvio.

Figuras: `figuras/09_per_capita_nacional.png`, `figuras/10_emendas_per_capita_uf.png`.
