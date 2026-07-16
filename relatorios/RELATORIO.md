# Relatório — Sucuri: Detecção de anomalias em despesas com Ensino Superior

**Fase reportada:** Fase 0 — Infraestrutura do projeto (ROADMAP.md, tarefas 0.1 e 0.2)
**Data:** 2026-07-16
**Responsável pela execução:** modelo de linguagem (Sonnet 5), seguindo CLAUDE.md e ROADMAP.md

---

## 1. Objetivo desta fase

A Fase 0 do ROADMAP não produz análises sobre as despesas em si — seu objetivo é
transformar o projeto de um único script (`coletar_despesas.py`) em uma base de
código reprodutível, testável e reutilizável pelas fases seguintes (qualidade
de dados, deflação, detecção de anomalias). Este relatório documenta **o que
foi feito**, não interpretações sobre os dados de despesas (essas começam na
Fase 1/2 e serão anexadas às próximas seções deste mesmo documento).

## 2. Tarefa 0.1 — Empacotamento e ambiente

### 2.1 Estrutura criada

```
pyproject.toml            # projeto gerenciado por uv (PEP 621 + hatchling)
uv.lock                   # lockfile de dependências
src/sucuri/
  __init__.py
  api.py                  # cliente da API do Portal da Transparência
  features.py             # engenharia de variáveis e construção dos painéis A/B
  persistencia.py         # salvamento de CSV/Parquet/JSON bruto e dicionário
  utils.py                # brl_para_float, razao_segura, classificar_instituicao
analises/                 # reservado para as fases 1–2 (vazio nesta fase)
relatorios/
  figuras/                # reservado para as fases 1–2 (vazio nesta fase)
  latex/                  # este relatório em LaTeX/PDF
tests/
  __init__.py
  test_utils.py
  test_features.py
coletar_despesas.py       # CLI fino: apenas argparse + orquestração, importa de sucuri.*
```

### 2.2 Migração de código

Toda a lógica reutilizável de `coletar_despesas.py` foi movida para o pacote
`src/sucuri/`, preservando exatamente o comportamento original (mesmos
parâmetros de API, mesmas fórmulas, mesmo formato de saída):

| Função/constante | Origem (script único) | Destino |
|---|---|---|
| `brl_para_float`, `_razao_segura`, `classificar_instituicao` | topo do script | `sucuri/utils.py` (renomeada para `razao_segura`, pública) |
| `carregar_chave_api`, `criar_sessao`, `requisitar`, `coletar_paginado`, `coletar_intervalo`, constantes de endpoint/rate limit | seção "Coleta genérica" | `sucuri/api.py` |
| `construir_df_funcional`, `construir_df_instituicao`, `_indicadores_execucao`, `_features_serie_temporal`, `_consolidar_flags` | seções (A)/(B) e "Engenharia de variáveis" | `sucuri/features.py` (funções internas tornadas públicas: `indicadores_execucao`, `features_serie_temporal`, `consolidar_flags`) |
| `salvar_dataset`, `escrever_dicionario`, `DICIONARIO`, `resumir` | seção "Persistência" | `sucuri/persistencia.py` |

O arquivo `coletar_despesas.py` (antes `coletar_despesas_ensino_superior.py`)
ficou reduzido a ~125 linhas: apenas `argparse`, orquestração das coletas (A) e
(B), e chamadas às funções do pacote. Nenhuma fórmula ou regra de negócio foi
alterada durante a migração — apenas reorganizada em módulos.

### 2.3 Dependências (`pyproject.toml`)

Gerenciadas por `uv`: `pandas`, `pyarrow`, `requests`, `python-dotenv`,
`scikit-learn`, `scipy`, `matplotlib` (produção); `ruff`, `pytest`
(grupo `dev`). `uv sync --group dev` cria o ambiente virtual e resolve o
lockfile em poucos segundos.

### 2.4 Verificação dos critérios de aceite

| Critério (ROADMAP 0.1) | Resultado |
|---|---|
| `uv run python coletar_despesas.py --help` funciona | ✅ Exibe o help completo, docstring preservada |
| `uv run pytest` roda (mesmo com 0 testes) | ✅ Rodou sem erros antes da tarefa 0.2 popular os testes |
| `uv run ruff check .` sem erros | ✅ `All checks passed!` |

## 3. Tarefa 0.2 — Testes unitários das funções críticas

### 3.1 Cobertura

37 testes em 2 arquivos, cobrindo exatamente as funções indicadas no ROADMAP:

**`tests/test_utils.py`** (23 testes)
- `brl_para_float`: formato brasileiro com separador de milhar (`1.059.473.395,24`),
  sem separador de milhar, `None`, string vazia, string só com espaços, valor já
  numérico (`int`/`float`), entrada inválida (`"abc"` → `NaN`), valor negativo.
- `razao_segura`: divisão normal e **denominador zero → `NaN`** (em vez de erro
  ou `inf`).
- `classificar_instituicao`: um caso por categoria (Universidade Federal,
  Hospitalar/EBSERH, Instituto Federal, CEFET, CAPES, Fundo FNDE/FIES, Educação
  Básica, Outros/Administração), mais `None` e string vazia.

**`tests/test_features.py`** (14 testes)
- `indicadores_execucao`: taxas e saldos em caso normal; **`empenhado == 0` →
  taxas `NaN` sem exceção**; disparo isolado de cada flag de incoerência
  (`pago > empenhado`, `liquidado > empenhado`, valor negativo); ausência de
  falso positivo em valores coerentes.
- `features_serie_temporal`: variação anual ano a ano; disparo de
  `flag_salto_anual` acima de 100%; **série com desvio-padrão zero (valores
  constantes) não gera erro de divisão por zero** e produz `zscore` `NaN` em
  vez de indefinido; série com uma única observação; independência entre
  séries diferentes agrupadas no mesmo DataFrame.
- `consolidar_flags`: nenhuma flag ativa, uma flag ativa, flag extra
  (`flag_atipico_entre_pares`) considerada, valores nulos tratados como
  `False` na consolidação.

Os dois casos de borda explicitamente pedidos no ROADMAP — **divisão por
zero** e **série com desvio-padrão zero** — estão cobertos e passam sem
exceções, confirmando que as fórmulas originais (`.replace(0, pd.NA)`) já
protegiam contra isso; os testes tornam essa garantia explícita e verificável
automaticamente.

### 3.2 Resultado da execução

```
uv run pytest -v
============================== 37 passed in 0.67s ==============================

uv run ruff check .
All checks passed!
```

*Aceite (ROADMAP 0.2):* ✅ `uv run pytest` verde; as três funções citadas no
ROADMAP (`brl_para_float`/`classificar_instituicao`,
`_indicadores_execucao`, `_features_serie_temporal`, `_consolidar_flags`)
têm cobertura direta.

## 4. Validação de não regressão

Após a migração, foi confirmado por busca no repositório que não restou
nenhuma referência às funções privadas antigas (`_indicadores_execucao`,
`_features_serie_temporal`, `_consolidar_flags`, `_razao_segura`) fora do
pacote `sucuri`, e que os módulos migrados importam e executam corretamente
(`from sucuri.utils import ...`, `from sucuri.features import ...`, `from
sucuri.api import ...`). Os dados já coletados em `dados/` (dois conjuntos,
2014–2026) não foram alterados nesta fase — nenhuma recoleta foi executada.

## 5. Ressalvas e decisões registradas

- As funções antes privadas (`_indicadores_execucao` etc.) foram tornadas
  públicas (sem `_`) ao mover para `sucuri/features.py`, pois passam a ser a
  API pública do pacote reutilizada pelas fases seguintes. Isso é uma mudança
  de visibilidade, não de comportamento.
- `analises/` e `relatorios/figuras/` foram criados vazios nesta fase — serão
  populados a partir da Fase 1/2 do ROADMAP.
- Nenhum dado foi recoletado; a chave `GOVBR_API_KEY` não foi lida nem
  impressa durante esta fase (apenas os testes unitários, que não fazem
  chamadas de rede, foram executados).

## 6. Estado do ROADMAP

Tarefas 0.1 e 0.2 marcadas como concluídas em `ROADMAP.md`.

---

# Parte II — Fase 1: Qualidade e preparação dos dados

**Data:** 2026-07-16
**Responsável pela execução:** modelo de linguagem (Sonnet 5), seguindo CLAUDE.md e ROADMAP.md

Esta parte cobre as tarefas 1.1, 1.2 e 1.3 do ROADMAP — a primeira parte do
relatório com interpretação de dados reais de despesas. Ao final desta fase,
o conjunto recomendado para toda análise de anomalia (Fase 2 em diante)
passa a ser `dados/*_v2.{csv,parquet}`, não mais os arquivos originais da
Fase 0.

## II.1 Tarefa 1.1 — Relatório de qualidade dos dados

**Método:** `analises/01_qualidade.py` roda sobre os dados como saíram da
Fase 0 (nominais, sem tratamento) e produz `relatorios/01_qualidade.md`
com seis checagens: cobertura por ano, % de zeros por coluna monetária,
séries curtas, duplicatas, incoerências de execução
(`pago > empenhado` etc.) e uma checagem descritiva de ordem de grandeza.

**Resultados e interpretação:**

1. **Cobertura por ano** — confirma que **2026 é ano parcial**: no Conjunto
   B (todos os órgãos do MEC), o total pago cai de R$ 204,7 bi em 2025 para
   R$ 114,6 bi em 2026 (coleta feita em julho/2026) — não é uma queda de
   gasto, é cobertura incompleta do exercício. Já era uma ressalva conhecida
   em `CLAUDE.md`; a tarefa 1.1 apenas quantifica o efeito.
2. **Zeros** — Conjunto A tem ~79–81% de zeros nas colunas monetárias
   (granularidade fina: programa × ação, muitas combinações sem execução em
   um dado ano); Conjunto B tem 0% de zeros (granularidade grossa: total do
   órgão). Não é erro, é a natureza dos dois endpoints — confirma a ressalva
   já registrada em `CLAUDE.md`.
3. **Séries curtas** — 125 de 239 séries do Conjunto A (52,3%) têm menos de
   5 anos de observação. Média/desvio-padrão calculados sobre 1–4 pontos não
   sustentam um z-score confiável — tratado na tarefa 1.3 (`serie_curta`).
4. **Duplicatas — achado novo desta tarefa, não estava documentado antes.**
   O Conjunto A tem 69 linhas duplicadas em `(ano, chave_serie)`. Investigação
   da causa-raiz: não são séries diferentes colidindo por acaso — é a API do
   Portal da Transparência retornando, para o mesmo `codigoPrograma`/
   `codigoAcao`, duas grafias do nome do programa/ação (ex.: "BRASIL
   UNIVERSITARIO" vs. "BRASIL UNIVERSITÁRIO", "BOLSA PERMANENCIA" vs.
   "BOLSAPERMANENCIA" sem espaço) — aparentemente uma correção de texto na
   fonte que não substituiu o registro antigo. Em 67 dos 69 grupos os dois
   registros têm valores idênticos (em geral ambos zero); em **2 grupos os
   valores divergem** — um registro carrega o valor real e o outro fica
   zerado (exemplo: "CONCESSÃO DE BOLSA PERMANÊNCIA", 2014, R$ 77,5 milhões
   empenhados na grafia correta vs. R$ 0 na grafia truncada). **Risco
   concreto:** se não tratado, um detector de anomalia ingênuo poderia
   confundir a alternância entre as duas grafias com um "salto anual" de 0
   para um valor alto — um falso positivo criado por duplicidade de texto na
   fonte, não por um evento de gasto real. Corrigido na tarefa 1.3 por
   agregação (soma) das duplicatas antes de qualquer cálculo de série
   temporal.
5. **Incoerências de execução** — apenas 1 linha em todo o Conjunto A com
   `pago > empenhado` (2026, ação de regulação/supervisão de cursos:
   empenhado R$ 67, pago R$ 103.240) e nenhuma no Conjunto B. Amostra pequena
   demais para conclusão — fica como candidata a checagem manual, não como
   erro confirmado; nenhuma linha com valor negativo em nenhum dos conjuntos.
6. **Ordem de grandeza** — total pago em 2025: ~R$ 204,7 bi (Conjunto B, MEC
   completo) e ~R$ 41,1 bi (Conjunto A, só subfunção 364). Ambos compatíveis
   com a ordem de grandeza publicamente conhecida do orçamento do MEC
   (dezenas de bilhões de reais/ano) — sem indício de erro de unidade. Uma
   validação linha a linha contra a dotação do SIOP fica para a tarefa 4.2.

Relatório completo: `relatorios/01_qualidade.md`.

## II.2 Tarefa 1.2 — Deflacionamento pelo IPCA

**Método:** o pré-requisito (IPCA anual) foi **automatizado** em
`analises/00_baixar_ipca.py` — baixa a série mensal do IPCA (Banco Central,
SGS série 433, API pública sem cadastro) e calcula o acumulado por ano
civil. `src/sucuri/deflacao.py` constrói um índice de preços encadeado a
partir desses acumulados anuais e converte valores nominais em reais do
ano-base (razão entre os índices de dois anos quaisquer = fator de correção
inflacionária entre eles). `analises/01b_deflacionar.py` aplica isso aos
dois conjuntos, gerando `empenhado_real`/`liquidado_real`/`pago_real`.

**Resultados e interpretação:**

- IPCA acumulado por ano (2014–2026, sendo 2026 parcial — só janeiro a
  junho): variação anual entre 2,9% (2017) e 10,7% (2015), com dois anos de
  inflação alta (2015: 10,7%; 2021: 10,1%) intercalados por anos mais
  estáveis (2017–2019: 3,0–4,3%). Acumulado 2014→2025: fator de correção de
  **1,824×** — ou seja, R$ 1,00 de 2014 equivale a R$ 1,82 de poder de
  compra de 2025.
- **Ano-base escolhido: 2025** (último ano com os 12 meses de IPCA
  disponíveis — 2026 é parcial tanto nos dados de despesa quanto no IPCA,
  então não pode ser base de comparação).
- **Checagem de sanidade (critério de aceite do ROADMAP):** valores de 2014
  ficam maiores após a correção — pago nominal de 2014 no Conjunto A é
  R$ 25,89 bi; pago real (R$ de 2025) é **R$ 47,21 bi** (fator 1,824,
  batendo com o fator do IPCA acumulado). Mesmo fator no Conjunto B
  (R$ 104,71 bi nominal → R$ 190,94 bi real). Confirma que a implementação
  está correta: a inflação de 12 anos quase dobra o valor nominal antigo
  quando expresso em reais de hoje.
- **Interpretação para a Fase 2:** qualquer comparação de crescimento de
  gasto entre anos distantes (ex.: 2014 vs. 2025) DEVE usar as colunas
  `*_real`; usar as colunas nominais superestimaria o crescimento real em
  até ~82 pontos percentuais só pelo efeito da inflação acumulada.

## II.3 Tarefa 1.3 — Tratamento do ano parcial e revisão das flags

**Método:** `analises/01c_ano_parcial_e_flags.py` parte de `dados/*_real.*`
e (1) deduplica o Conjunto A somando as colunas monetárias das linhas
identificadas na tarefa 1.1 (mesma `chave_serie`/ano, grafias diferentes);
(2) marca `ano_parcial=True` no ano detectado pelo carimbo de
`dados/raw/*.json` (`sucuri.persistencia.detectar_ano_coleta`); (3) marca
`serie_curta=True` nas séries com menos de 5 anos de observação; (4)
recalcula `variacao_pago_aa`, `zscore_pago`, `zscore_robusto_pago` e (só
Conjunto B) `zscore_pago_entre_pares` — **com base em `pago_real`, não mais
`pago` nominal** — usando como base estatística só as linhas elegíveis
(nem `ano_parcial` nem `serie_curta`); as demais linhas recebem `NaN`
nessas métricas e `False` nas flags derivadas.

**Decisão de desenho não prevista literalmente no ROADMAP, registrada
aqui:** a tarefa 1.2 já deflaciona os valores; fazia sentido que a tarefa
1.3, ao recalcular z-scores/variação anual, usasse `pago_real` em vez de
`pago` nominal — comparar valores nominais entre anos distantes misturaria
inflação com variação real de gasto, o problema que a tarefa 1.2 existe
para resolver. As funções de `src/sucuri/features.py` foram generalizadas
(parâmetro `coluna_valor`) para suportar isso sem duplicar código nem
quebrar o comportamento (testado) da Fase 0.

**Resultados e interpretação:**

| Conjunto | Linhas antes da dedup | Linhas depois | `flag_anomalia` antes¹ | `flag_anomalia` depois² |
|---|---:|---:|---:|---:|
| A (funcional-programático) | 1.318 | 1.249 (-69) | 41 | **19** |
| B (por instituição) | 1.484 | 1.484 (sem duplicatas) | 73 | **58** |

¹ Pipeline original da Fase 0: nominal, sem dedup, sem exclusão de ano
parcial/série curta. ² Pipeline da tarefa 1.3: `pago_real`, deduplicado,
excluindo ano parcial (2026) e séries curtas da base estatística.

- **A queda de 41→19 no Conjunto A** vem de três efeitos somados: a
  deduplicação (remove falsos "saltos" de grafia), a exclusão do ano parcial
  (remove quedas artificiais de 2026) e a exclusão de séries curtas (remove
  z-scores calculados sobre 1–4 pontos, estatisticamente instáveis). Não é
  possível, com os dados agregados no log, atribuir a queda a um único
  efeito isoladamente — isso fica registrado como limitação e pode ser
  decomposto em uma iteração futura se for necessário isolar a contribuição
  de cada fator.
- **A queda de 73→58 no Conjunto B** vem só da exclusão do ano parcial (o
  Conjunto B não tem duplicatas nem séries curtas — todas as ~115
  instituições têm histórico desde 2014).
- **Nenhuma flag de anomalia remanescente é baseada no ano parcial** —
  critério de aceite do ROADMAP cumprido: toda linha com `ano_parcial=True`
  tem `flag_anomalia_zscore=False`, `flag_anomalia_robusto=False`,
  `flag_salto_anual=False` e (no Conjunto B) `flag_atipico_entre_pares=False`
  por construção (excluídas do cálculo, não apenas filtradas depois).
- `dados/DICIONARIO.md` foi atualizado com uma nova seção descrevendo os
  conjuntos `_real` e `_v2`, deixando explícito que **`_v2` é o conjunto
  recomendado para a Fase 2** — os demais (`_real` e os originais da Fase 0)
  são estágios intermediários do pipeline, não o ponto de partida para
  detecção de anomalias.

## II.4 Estado do ROADMAP após a Fase 1

Tarefas 1.1, 1.2 e 1.3 marcadas como concluídas em `ROADMAP.md`, com os
desvios de escopo (deduplicação do Conjunto A, uso de `pago_real` nas
métricas de série temporal) documentados tanto lá quanto nesta seção.

---

# Parte III — Fase 2: Detecção estatística de anomalias

**Data:** 2026-07-16
**Responsável pela execução:** modelo de linguagem (Sonnet 5), seguindo CLAUDE.md e ROADMAP.md

Cobre as tarefas 2.1 a 2.5. Toda a fase parte de `dados/*_v2.{csv,parquet}`
(saída da Fase 1). Cada tarefa tem relatório próprio detalhado
(`relatorios/02_eda.md` a `relatorios/06_casos.md`); esta parte resume
método, resultado e interpretação de cada uma, com foco nos achados que
persistem para além do relatório individual.

## III.1 Tarefa 2.1 — Análise exploratória com foco em anomalias

**Método:** `analises/02_eda.py` produz 4 figuras e 6 seções em
`relatorios/02_eda.md`: evolução anual, top 10 ações do Conjunto A,
distribuição de taxas por tipo de instituição (B), ranking de
instituições, linhas já flageadas e uma lista de 20 candidatas a
investigação.

**Resultados e interpretação:**

- **Trajetória em U, não em queda:** ambos os conjuntos caem de 2017/2018
  até um piso em **2021** (Conjunto B: R$ 195,1 bi → R$ 153,3 bi, -21,4%
  real) e se recuperam até **2025, novo máximo da série** (R$ 204,7 bi).
  Esse padrão de recuperação pós-2021 volta a aparecer, de forma
  independente, na tarefa 2.5 (concentração de casos em 2025).
- **Achado estrutural sobre o próprio Conjunto A:** as duas maiores ações
  em valor acumulado (juntas ~R$ 343 bi, mais que as outras 8 do top 10
  somadas) são a mesma ação genérica de **folha de pagamento** ("Ativos
  Civis da União") sob dois programas diferentes — a subfunção "Ensino
  Superior" no Conjunto A é majoritariamente pessoal, não bolsas ou
  custeio. Qualquer variação nessa linha deve ser lida à luz de reajuste
  salarial, não evento pontual.
- **Ressalva reforçada:** o 1º colocado do ranking de instituições (FNDE,
  R$ 89,78 bi em 2025 — 7,5× o 2º colocado) não é "a maior despesa de
  ensino superior" — o FNDE administra programas de educação básica além
  de FIES, e o Conjunto B soma todas as funções do órgão. Reforça a
  ressalva já registrada em `CLAUDE.md`.
- Vários outliers na cauda baixa de `taxa_pagamento` (mínimo 0,098 em
  Universidade Federal) ficam como candidatos não investigados
  individualmente nesta tarefa — insumo para 2.3.

## III.2 Tarefa 2.2 — Lei de Benford

**Método:** `analises/03_benford.py` aplica o teste de primeiro/segundo
dígito (qui-quadrado + MAD de Nigrini) sobre `empenhado`/`pago` nominais
(não deflacionados — deflação aplica um fator diferente por ano, o que
alteraria dígitos por um motivo alheio ao fenômeno testado), no Conjunto A
completo e no Conjunto B por `tipo_instituicao`.

**Resultados e interpretação:**

- **Achado principal: o Conjunto A é insuficiente para o teste.** Depois
  do filtro > R$ 1.000, sobram só 225–254 valores por grupo — abaixo do
  limiar de 300 adotado. O primeiro dígito parece conforme mas o segundo
  não, no mesmo par de colunas — inconsistência típica de amostra
  subdimensionada, não conformidade real. Conclusão registrada: o painel
  agregado (uma linha por ano×programa×ação) não tem volume para Benford
  ser informativo; só lançamentos individuais (tarefa 3.1) teriam.
- **Conjunto B, grupos bem-dimensionados (`Universidade Federal`, n=791;
  `Instituto/CEFET/Escola Técnica`, n=480): não conformidade em ambos**,
  com o mesmo padrão — excesso do dígito 1 (39,1% vs. 30,1% esperado) e
  déficit dos dígitos 3–4. Explicação estrutural, não fraude: cada linha é
  o orçamento total anual de instituições do mesmo tipo, uma grandeza
  concentrada numa faixa de magnitude estreita — Benford pressupõe várias
  ordens de grandeza, condição que totais institucionais homogêneos violam
  por construção.
- Os demais 10 de 14 grupos do Conjunto B (CAPES, Fundo, Educação Básica,
  Hospitalar) têm amostra insuficiente (<300) e ficam explicitamente
  marcados como inconclusivos, mesmo quando o qui-quadrado é
  "significativo" — significância não substitui tamanho de amostra na
  classificação adotada.

## III.3 Tarefa 2.3 — Modelos não supervisionados (Isolation Forest + LOF)

**Método:** `analises/04_outliers.py` roda os dois modelos sobre 5
features padronizadas (`pago_real`, `taxa_liquidacao`, `taxa_pagamento`,
`variacao_pago_aa`, `restos_a_pagar_frac`) — Conjunto A como um único
grupo, Conjunto B por `tipo_instituicao` (grupos com <20 linhas elegíveis
pulados: CAPES, Educação Básica, Fundo). Gera `dados/*_scores.parquet`
com `score_anomalia`/`rank_anomalia`.

**Bug real encontrado e corrigido durante a implementação:** ao processar
o Conjunto B por grupo, cada grupo produzia ranks locais (1..n do próprio
grupo) — concatenar sem recalcular gerava várias linhas empatadas em
`rank_anomalia=1` (uma por grupo) e quebrava tanto a seleção de "top 20"
quanto a matriz de concordância. Corrigido com
`sucuri.outliers.recalcular_ranks_globais`, que reconstrói ranks globais a
partir dos scores normalizados por método — coberto por teste de
regressão (`tests/test_outliers.py`).

**Resultados e interpretação:**

- Concordância entre os dois métodos (top 10% de cada): Jaccard 0,60 no
  Conjunto A, 0,39 no B — concordância parcial esperada (isolamento global
  vs. densidade local capturam desvios diferentes).
- Concordância com `flag_anomalia` (Fase 1): sobreposição parcial em
  ambos os conjuntos — os modelos multivariados usam informação (nível de
  gasto, taxas) que as flags de série temporal isoladas não capturam.
- Dois padrões no top 20 do Conjunto B já têm explicação: as universidades
  da expansão 2013–2014 (mesmo efeito de rampa da tarefa 2.1) e a UFRJ,
  que aparece 4 vezes — possivelmente dominância de escala dentro do grupo
  `Universidade Federal` (791 linhas sem subdivisão por porte), não
  comportamento atípico.

## III.4 Tarefa 2.4 — Séries temporais por instituição (Theil–Sen)

**Método:** `analises/05_series.py` ajusta uma tendência robusta de
Theil–Sen por instituição (Conjunto B, ≥8 anos elegíveis, 111
instituições) sobre `pago_real`, e sinaliza resíduos > 2,5 desvios
robustos (MAD × 1,4826). Gera `dados/eventos_series.csv` (40 eventos).

**Bug real encontrado e corrigido:** quando a maioria dos pontos de uma
série segue a tendência de Theil–Sen exatamente, o MAD dos resíduos pode
ser zero — o código original pulava a série inteira nesse caso (`continue`
antes de qualquer verificação), descartando exatamente o caso mais óbvio
de outlier (um ponto isolado destoando de uma tendência perfeita nos
demais). Corrigido para tratar desvio-robusto-zero como "qualquer resíduo
diferente do valor dominante é, por definição, extremo" — coberto por
teste de regressão. Uma segunda iteração do fix corrigiu a comparação
(contra a mediana dos resíduos, não contra zero — o intercepto de
Theil-Sen não necessariamente zera o resíduo "normal").

**Resultados e interpretação:**

- Sobreposição com `flag_salto_anual` (Fase 1): **apenas 1 dos 40 eventos
  (2%)** também está marcado como salto anual — achado a registrar, não
  defeito. `flag_salto_anual` compara só com o ano anterior (sensível a
  mudanças abruptas de 1 ano); o resíduo de Theil–Sen compara com a
  tendência de toda a série (sensível a platôs de vários anos que nenhum
  ano individual sinalizaria). Os dois critérios são complementares, quase
  sem redundância.
- 4 das instituições no topo (Cariri, Oeste da Bahia, Sul da Bahia, Sul e
  Sudeste do Pará, evento em 2014) são o mesmo padrão de universidades
  novas já visto em 2.1/2.3 — já têm 12 anos de histórico hoje, passam no
  critério de ≥8 anos, mas o ano de implantação continua sendo um resíduo
  extremo em relação à própria tendência madura.
- **Achados sem explicação estrutural** (candidatos reais a checagem
  manual): Universidade Federal Rural do Rio de Janeiro (queda sustentada
  2019→2021, recuperação parcial) e Fundação Universidade Federal do Vale
  do São Francisco (queda até 2021, salto acentuado em 2024–2025) — únicas
  instituições consolidadas (não recém-criadas) com padrão de oscilação
  não explicado nesta fase.

## III.5 Tarefa 2.5 — Consolidação e priorização de casos

**Método:** `analises/06_casos.py` unifica `flag_anomalia` (Fase 1),
`score_anomalia` (2.3) e o desvio de Theil–Sen (2.4, só Conjunto B) por
`(conjunto, entidade, ano)`. A Lei de Benford (2.2) não entra — é teste de
conformidade do grupo, não produz sinal por entidade. Um caso só entra na
lista se algum sinal **disparou de fato** (`flag_anomalia=True`, ou
`score_anomalia` no top 10% do seu grupo, ou presença em
`eventos_series.csv`) — não basta `score_anomalia` ser positivo, que é
quase sempre verdade por ser um rank contínuo. Gera
`dados/casos_priorizados.csv`.

**Dois bugs reais encontrados e corrigidos durante a implementação:**
1. O filtro inicial (`score_combinado > 0`) deixava passar 1.363 das
   ~2.467 linhas elegíveis — quase tudo — porque `score_anomalia` (2.3) é
   um rank contínuo quase sempre positivo. Substituído pelo critério de
   disparo discreto acima; resultado caiu para 176 casos candidatos.
2. A ordenação por `score_combinado` sozinho enterrava casos com múltiplos
   sinais concordantes atrás de casos com um único sinal binário
   (`flag_anomalia=1.0` sozinho já soma média 1,00, empatando com casos de
   2-3 sinais). Corrigido para ordenar primeiro por número de sinais
   concordantes, depois por score — exatamente o que o texto do relatório
   já afirmava ser a prioridade (triangulação de métodos independentes).

**Resultados e interpretação:**

- 176 casos candidatos (29 no Conjunto A, 147 no B); 33 têm o número
  máximo de sinais concordantes (maior confiança).
- **Achado de síntese, não visível em nenhuma tarefa isolada:** 2025
  responde por 35 dos 176 casos (20%, vs. ~8% esperado por distribuição
  uniforme) e por 16 dos 33 casos de maior confiança (quase metade). Isso
  bate com o achado da tarefa 2.1 de que 2025 é o novo máximo real da
  série — leitura recomendada: boa parte dos casos de 2025 provavelmente
  não são eventos independentes, e sim a mesma recuperação orçamentária
  macro (pós-2021) se manifestando instituição por instituição, já que
  cada modelo de tendência olha só a própria série. Isso não invalida os
  casos, mas muda a pergunta de investigação de "por que este salto" para
  "esta instituição cresceu mais que a média do setor, e por quê".
- Casos com nota de "padrão já identificado" (universidades novas, folha
  de pagamento, dominância de escala) aparecem na lista mas devem ser
  priorizados por último — a distinção entre "estatisticamente extremo" e
  "já explicado" só existe porque as tarefas 2.1–2.4 investigaram cada
  padrão recorrente manualmente; o score combinado sozinho não sabe fazer
  essa distinção.

## III.6 Estado do ROADMAP após a Fase 2

Tarefas 2.1 a 2.5 marcadas como concluídas em `ROADMAP.md`. Três bugs reais
foram encontrados e corrigidos durante a própria implementação desta fase
(ranks locais não recalculados globalmente em 2.3; MAD-zero descartando o
outlier mais óbvio em 2.4; filtro de "caso candidato" deixando passar
quase tudo em 2.5) — todos cobertos por testes de regressão em
`tests/`. Próxima tarefa pendente: **Fase 3 — Enriquecimento com outros
dados do Portal da Transparência** (contratos, licitações, sanções,
convênios, CPGF, emendas), que depende de novos coletores (ver ROADMAP.md).

---

## Instrução de manutenção deste relatório

A partir da Fase 1, toda nova tarefa do ROADMAP que gerar análise, medida
estatística ou modelo deve **acrescentar uma seção a este arquivo** (e à
versão LaTeX em `relatorios/latex/relatorios.tex`) com: o que foi medido, o
método usado, o resultado numérico e sua interpretação — nunca apenas o
código ou o caminho do arquivo gerado. Ver `CLAUDE.md`, seção "Registro de
análises e relatórios".
