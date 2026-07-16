# ROADMAP — Detecção de anomalias em despesas com Ensino Superior

Plano de trabalho em fases. Cada tarefa é autocontida e pode ser executada por
outro modelo (ex.: Sonnet 5) sem contexto adicional além de CLAUDE.md,
`dados/DICIONARIO.md` e desta descrição. Marque `[x]` ao concluir e anote
desvios ao lado da tarefa.

Convenções para todas as tarefas:
- Ambiente: `uv run --with pandas,pyarrow,... python ...` até a tarefa 0.1
  criar o `pyproject.toml`; depois, `uv run python ...`.
- Notebooks/relatórios em `analises/`, código reutilizável em `src/sucuri/`,
  saídas de dados em `dados/`, figuras em `relatorios/figuras/`.
- Sempre excluir ou marcar o ano corrente (parcial) nas análises temporais.
- Nunca ler/imprimir a chave `GOVBR_API_KEY`.

---

## Fase 0 — Infraestrutura do projeto

- [x] **0.1 Empacotamento e ambiente** — concluída em 2026-07-16.
  Criado `pyproject.toml` (gerenciado por `uv`, hatchling) com as dependências
  planejadas + `uv.lock`. Estrutura `src/sucuri/{api,features,persistencia,utils}.py`,
  `analises/`, `relatorios/figuras/`, `relatorios/latex/`, `tests/` criada.
  Lógica reutilizável de `coletar_despesas.py` migrada para `src/sucuri/` sem
  alterar comportamento (mesmas fórmulas/parâmetros); `coletar_despesas.py`
  ficou como CLI fino (~125 linhas) que importa do pacote.
  *Aceite:* ✅ os três critérios (help, pytest, ruff) verificados — ver
  `relatorios/RELATORIO.md`, seção 2.
  *Desvio:* funções antes privadas (`_indicadores_execucao`,
  `_features_serie_temporal`, `_consolidar_flags`) tornadas públicas (sem
  `_`) ao virarem API do pacote — mudança de visibilidade, não de
  comportamento.

- [x] **0.2 Testes das funções críticas** — concluída em 2026-07-16.
  37 testes unitários (`tests/test_utils.py`, `tests/test_features.py`) para
  `brl_para_float`, `razao_segura`, `classificar_instituicao`,
  `indicadores_execucao`, `features_serie_temporal`, `consolidar_flags`,
  incluindo divisão por zero e série com desvio-padrão zero.
  *Aceite:* ✅ `uv run pytest` → 37 passed; `uv run ruff check .` →
  All checks passed. Detalhes em `relatorios/RELATORIO.md`, seção 3.

## Fase 1 — Qualidade e preparação dos dados existentes

- [x] **1.1 Relatório de qualidade dos dados** — concluída em 2026-07-16.
  `analises/01_qualidade.py` → `relatorios/01_qualidade.md`. Achado
  principal (não previsto no ROADMAP original): 69 linhas do Conjunto A
  duplicadas em `(ano, chave_serie)` por grafia divergente do mesmo
  programa/ação na fonte (acentuação/espaçamento) — em 2 dos 69 grupos os
  valores monetários divergem entre as grafias, risco real de o valor
  "sumir" em um ano e "reaparecer" no seguinte, imitando um salto de
  anomalia. Tratado na tarefa 1.3 (deduplicação por soma).
  *Aceite:* ✅ relatório com as 6 seções pedidas; duplicatas documentadas com
  causa-raiz. Detalhes em `relatorios/RELATORIO.md`, seção II.1.

- [x] **1.2 Deflacionamento pelo IPCA** — concluída em 2026-07-16.
  IPCA obtido via automação (EXTERNAL.md, E1): `analises/00_baixar_ipca.py`
  baixa a série mensal do Banco Central (SGS 433, pública) e calcula o
  acumulado anual em `dados/externos/ipca_anual.csv`. `src/sucuri/deflacao.py`
  criado; `analises/01b_deflacionar.py` gera `dados/*_real.{csv,parquet}`
  (ano-base 2025, último ano completo).
  *Aceite:* ✅ pago de 2014 nominal R$25,89 bi → real R$47,21 bi (fator
  1,824×, Conjunto A); testes com fator de deflação conhecido em
  `tests/test_deflacao.py`. Detalhes em `relatorios/RELATORIO.md`, seção II.2.

- [x] **1.3 Tratamento do ano parcial e revisão das flags** — concluída em
  2026-07-16. `analises/01c_ano_parcial_e_flags.py` → `dados/*_v2.{csv,parquet}`.
  `ano_parcial`/`serie_curta` adicionadas; z-scores/variação anual
  recalculados com base em `pago_real` (não nominal — desvio de escopo
  registrado abaixo) excluindo essas linhas da base estatística; Conjunto A
  também deduplicado (achado da tarefa 1.1) antes do recálculo.
  `dados/DICIONARIO.md` atualizado com seção sobre os conjuntos `_real`/`_v2`.
  *Aceite:* ✅ nenhuma flag de anomalia baseada em ano parcial; `flag_anomalia`
  41→19 (Conjunto A), 73→58 (Conjunto B), contagem completa em
  `relatorios/RELATORIO.md`, seção II.3.
  *Desvios registrados:* (1) z-scores/variação anual recalculados sobre
  `pago_real` em vez de `pago` nominal — não estava explícito no ROADMAP,
  mas é a continuação lógica da tarefa 1.2 (comparar nominal entre anos
  distantes reintroduziria o viés que a deflação corrige); `features_serie_temporal`
  e `zscore_entre_pares` foram generalizadas com parâmetro `coluna_valor`
  para isso, sem quebrar o comportamento (testado) da Fase 0. (2) a
  deduplicação do Conjunto A não estava prevista na tarefa 1.3 original —
  foi incorporada aqui por ser pré-requisito para o recálculo de séries
  temporais funcionar corretamente (ver achado da tarefa 1.1).

## Fase 2 — Detecção estatística de anomalias (dados atuais)

- [ ] **2.1 Análise exploratória com foco em anomalias**
  Notebook/script `analises/02_eda.py` → `relatorios/02_eda.md` + figuras:
  evolução do total real por ano (A e B); top 10 programas/ações por valor;
  distribuição de `taxa_liquidacao`/`taxa_pagamento` por tipo de instituição;
  ranking de instituições por `pago_real` per capita quando houver dados de
  matrículas (senão, absoluto); tabela das linhas já flageadas com leitura
  crítica (quais parecem artefato de dados vs. candidatas reais).
  *Aceite:* relatório em markdown com figuras salvas e uma seção
  "candidatas a investigação" com no máximo 20 linhas justificadas.

- [ ] **2.2 Lei de Benford (primeiro e segundo dígitos)**
  `analises/03_benford.py`: aplicar Benford sobre `empenhado` e `pago`
  (valores > R$ 1.000) no Conjunto A completo e, no B, por tipo de
  instituição. Estatísticas qui-quadrado e MAD (classificação de Nigrini);
  gráfico observado × esperado.
  *Aceite:* relatório `relatorios/03_benford.md` indicando conformidade por
  grupo, com a ressalva de que amostras pequenas (<300 valores) são
  inconclusivas — marcar esses grupos como "amostra insuficiente".

- [ ] **2.3 Modelos não supervisionados**
  `analises/04_outliers.py`: Isolation Forest e LOF sobre features
  padronizadas `[pago_real, taxa_liquidacao, taxa_pagamento,
  variacao_pago_aa, restos_a_pagar/empenhado]`, separadamente para A (por
  linha ano×ação) e B (por linha ano×órgão, dentro de cada
  `tipo_instituicao`). Comparar interseção dos dois métodos e com as
  `flag_*` existentes (matriz de concordância).
  *Aceite:* coluna `score_anomalia` e `rank_anomalia` salvas em
  `dados/*_scores.parquet`; relatório com top 20 por conjunto e concordância
  entre métodos.

- [ ] **2.4 Séries temporais por instituição**
  `analises/05_series.py`: para cada órgão do Conjunto B com ≥8 anos, ajustar
  tendência robusta (ex.: regressão de Theil–Sen ou STL anual simples) sobre
  `pago_real` e sinalizar resíduos > 2,5 desvios robustos. Comparar com
  `flag_salto_anual`.
  *Aceite:* lista de eventos (órgão, ano, desvio) em
  `dados/eventos_series.csv` com no máximo ~50 eventos, ordenada por desvio.

- [ ] **2.5 Consolidação e priorização de casos**
  `analises/06_casos.py`: unificar sinais de 2.1–2.4 em uma tabela de casos
  (`dados/casos_priorizados.csv`): entidade, ano, sinais que dispararam,
  valores envolvidos, score combinado (média dos ranks normalizados).
  *Aceite:* top 15 casos com justificativa textual de 1–2 frases cada em
  `relatorios/06_casos.md`; nenhuma referência a caso baseada em ano parcial.

## Fase 3 — Enriquecimento com outros dados do Portal da Transparência

Todos usam a mesma chave/sessão do coletor atual (respeitar rate limit).
Criar um coletor por tarefa em `src/sucuri/coletores/`, reutilizando
`requisitar`/`coletar_paginado`, salvando em `dados/` + `dados/raw/`.

- [ ] **3.1 Despesas por órgão × funcional (visão híbrida)**
  Endpoint `/despesas/por-orgao` não filtra subfunção, mas o endpoint de
  documentos (`/despesas/documentos`) e o download em lote (ver EXTERNAL.md,
  E2) permitem o recorte órgão × subfunção 364. Implementar a via API para
  2–3 universidades piloto (maiores do Conjunto B) e validar contra o total
  do Conjunto A.
  *Aceite:* `dados/despesas_univ_piloto_364.parquet` e nota de validação.

- [ ] **3.2 Contratos das instituições**
  Endpoint `/contratos` por `codigoOrgao` (usar os códigos do Conjunto B),
  anos 2018+. Features: valor contratado/aditivado, prazo, concentração de
  fornecedores por órgão (índice Herfindahl), % de dispensa/inexigibilidade.
  *Aceite:* `dados/contratos_mec.parquet` + relatório com órgãos no decil
  superior de concentração de fornecedores.

- [ ] **3.3 Licitações e compras**
  Endpoint `/licitacoes` por órgão: modalidade, valor, situação. Cruzar com
  3.2: contratos sem licitação correspondente, licitações desertas repetidas,
  fracionamento (múltiplas dispensas do mesmo órgão/fornecedor/objeto no ano
  logo abaixo do teto de dispensa).
  *Aceite:* `dados/licitacoes_mec.parquet` + lista de indícios de
  fracionamento com regra explícita e limiar documentado.

- [ ] **3.4 Sanções: CEIS, CNEP e acordos de leniência**
  Endpoints `/ceis`, `/cnep`, `/acordos-leniencia`. Cruzar CNPJs sancionados
  com fornecedores dos contratos de 3.2: contratos firmados com empresa já
  sancionada na data da assinatura é sinal forte.
  *Aceite:* `dados/sancoes.parquet` + `dados/contratos_com_sancionados.csv`
  (pode ser vazio; o cruzamento deve rodar de qualquer forma).

- [ ] **3.5 Convênios e transferências**
  Endpoint `/convenios` (concedente MEC/FNDE/CAPES): valores, convenentes,
  situação (adimplente/inadimplente), prestação de contas. Sinais:
  convenentes com múltiplos convênios inadimplentes; concentração de valores
  em poucos convenentes municipais.
  *Aceite:* `dados/convenios_mec.parquet` + top 20 convenentes por valor com
  status de prestação de contas.

- [ ] **3.6 Cartão de Pagamento do Governo Federal (CPGF)**
  Endpoint `/cartoes` filtrado aos órgãos do Conjunto B: gastos por portador,
  transações em fim de semana/dezembro, saques vs. compras, valores repetidos
  logo abaixo de limites de dispensa.
  *Aceite:* `dados/cpgf_mec.parquet` + relatório com as regras de red flag
  aplicadas e contagens por órgão.

- [ ] **3.7 Emendas parlamentares destinadas ao ensino superior**
  Endpoint `/emendas`: filtrar função Educação e beneficiários que são órgãos
  do Conjunto B. Sinais: dependência de emendas (% do orçamento), saltos
  ligados a anos eleitorais.
  *Aceite:* `dados/emendas_educacao.parquet` + série emendas/orçamento por
  instituição.

## Fase 4 — Cruzamentos com fontes externas (fora do portal)

Pré-requisito: arquivos baixados manualmente conforme EXTERNAL.md (E3–E5).
Se ausentes, pular a tarefa e sinalizar.

- [ ] **4.1 Custo por aluno (Censo da Educação Superior/INEP)**
  Cruzar matrículas por IES federal (E3) com `pago_real` do Conjunto B:
  `custo_por_aluno` por instituição/ano; outliers dentro de cada
  `tipo_instituicao` (z-score robusto).
  *Aceite:* `dados/custo_por_aluno.parquet` + ranking com ressalva explícita
  de que o denominador não separa hospital universitário/pesquisa.

- [ ] **4.2 Orçamento autorizado (LOA/SIOP)**
  Comparar dotação autorizada (E4) com empenhado do Conjunto A: execução
  <60% ou >100% da dotação por programa/ação.
  *Aceite:* tabela de divergências dotação × execução por ano.

- [ ] **4.3 Validação contra achados públicos (TCU/CGU)**
  Verificar se os top casos da tarefa 2.5 aparecem em acórdãos do TCU ou
  relatórios da CGU (E5). Objetivo: calibrar precisão dos sinais, não
  "confirmar culpa".
  *Aceite:* tabela caso × achado público (sim/não/não pesquisável) em
  `relatorios/validacao_tcu.md`.

## Fase 5 — Produto final

- [ ] **5.1 Relatório executivo**
  Consolidar tudo em `relatorios/RELATORIO.md`: metodologia, ressalvas,
  top casos priorizados com evidências de múltiplas fontes, limitações.
  Linguagem: indícios/atipicidades, nunca acusações.
- [ ] **5.2 Painel interativo (opcional)**
  Dashboard local (ex.: Streamlit) com séries por instituição, mapa de flags
  e drill-down para contratos/fornecedores.
- [ ] **5.3 Automação da recoleta**
  Tornar a coleta idempotente/incremental (só anos novos ou ano corrente) e
  documentar rotina mensal em EXTERNAL.md.

---

## Riscos e princípios (valem para todas as tarefas)
- **Anomalia estatística ≠ irregularidade.** Todo output deve usar linguagem
  de "atipicidade/indício a investigar".
- Ano parcial e séries curtas são as duas maiores fontes de falso positivo já
  identificadas — tratar antes de qualquer modelagem (fase 1).
- Comparações monetárias entre anos sempre em valores reais (IPCA).
- Rate limit da API (~90 req/min): coletas grandes (fase 3) podem levar horas;
  usar os downloads em lote do portal quando o volume for grande (EXTERNAL.md).
