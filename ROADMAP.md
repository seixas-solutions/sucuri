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

- [x] **2.1 Análise exploratória com foco em anomalias** — concluída em
  2026-07-16. `analises/02_eda.py` → `relatorios/02_eda.md` + 4 figuras.
  Achados: trajetória em U (piso 2021, novo máximo 2025); as 2 maiores
  ações do Conjunto A são a mesma ação genérica de folha de pagamento sob
  2 programas (achado estrutural novo); ranking de instituições sem per
  capita (dado de matrícula ainda não disponível — tarefa 4.1).
  *Aceite:* ✅ relatório com figuras + seção de 20 candidatas justificadas.
  Detalhes em `relatorios/RELATORIO.md`, seção III.1.
  *Desvio:* ranking do item 4 ficou em valor absoluto (per capita
  depende da tarefa 4.1/Censo INEP, ainda não coletado — sinalizado
  explicitamente no relatório, não simplesmente omitido).

- [x] **2.2 Lei de Benford** — concluída em 2026-07-16.
  `analises/03_benford.py` → `relatorios/03_benford.md` + 3 figuras.
  Achado principal: o Conjunto A (225–254 valores/grupo) é insuficiente
  para o teste, mesmo sendo "o conjunto completo" — abaixo do limiar de
  300. Conjunto B, grupos bem-dimensionados (Universidade Federal n=791,
  Instituto/CEFET n=480): não conformidade explicada estruturalmente
  (totais institucionais concentrados numa faixa estreita de magnitude).
  *Aceite:* ✅ relatório com classificação por grupo e amostras pequenas
  marcadas como inconclusivas. Detalhes em `relatorios/RELATORIO.md`,
  seção III.2.

- [x] **2.3 Modelos não supervisionados** — concluída em 2026-07-16.
  `analises/04_outliers.py` → `dados/*_scores.parquet` +
  `relatorios/04_outliers.md`. Isolation Forest + LOF sobre as 5 features
  do ROADMAP, B por `tipo_instituicao` (grupos <20 linhas pulados).
  *Aceite:* ✅ `score_anomalia`/`rank_anomalia` salvos; top 20 por
  conjunto; concordância IF×LOF (Jaccard 0,60 A / 0,39 B) e com
  `flag_anomalia`. Detalhes e bug corrigido (ranks locais não
  globalizados ao concatenar grupos de B) em `relatorios/RELATORIO.md`,
  seção III.3.

- [x] **2.4 Séries temporais por instituição** — concluída em 2026-07-16.
  `analises/05_series.py` → `dados/eventos_series.csv` (40 eventos) +
  `relatorios/05_series.md`. Theil–Sen sobre `pago_real`, ≥8 anos, 111
  instituições elegíveis.
  *Aceite:* ✅ eventos ordenados por desvio, comparados com
  `flag_salto_anual` (sobreposição de só 2% — achado de complementaridade
  entre os dois critérios). Detalhes e bug corrigido (MAD=0 descartava o
  outlier mais óbvio) em `relatorios/RELATORIO.md`, seção III.4.

- [x] **2.5 Consolidação e priorização de casos** — concluída em
  2026-07-16. `analises/06_casos.py` → `dados/casos_priorizados.csv`
  (176 casos) + `relatorios/06_casos.md`.
  *Aceite:* ✅ top 15 com justificativa textual; nenhum caso de ano
  parcial (excluído explicitamente antes de qualquer processamento).
  *Desvios:* (1) critério de "caso candidato" trocado de `score>0`
  (deixava passar 1.363 linhas, quase tudo) para disparo discreto de
  sinal (flag=True, top 10% de outlier, ou presença em eventos_series) —
  resultado caiu para 176; (2) ordenação trocada de só `score_combinado`
  para (nº de sinais concordantes, score) — um único sinal binário não
  deve empatar/superar 2-3 sinais triangulados. Achado de síntese: 2025
  concentra 20% dos casos (35/176) e quase metade da camada de maior
  confiança (16/33) — provavelmente reflexo da recuperação orçamentária
  macro pós-2021 (tarefa 2.1), não eventos independentes. Detalhes em
  `relatorios/RELATORIO.md`, seção III.5.

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
