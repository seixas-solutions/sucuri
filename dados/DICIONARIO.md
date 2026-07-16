# Dicionário de dados — Despesas com Ensino Superior

Fonte: Portal da Transparência (gov.br). Valores em reais (R$).

## Conjunto A — `despesas_ensino_superior.*` (funcional-programático)
Endpoint `/despesas/por-funcional-programatica`, função 12 (Educação),
subfunção 364 (Ensino Superior). Nível federal, por programa/ação.

| Coluna | Descrição |
|--------|-----------|
| ano | Ano do exercício orçamentário |
| codigoFuncao / funcao | Função (12 = Educação) |
| codigoSubfuncao / subfuncao | Subfunção (364 = Ensino Superior) |
| codigoPrograma / programa | Programa orçamentário |
| codigoAcao / acao | Ação orçamentária |
| chave_serie | Série temporal: programa-ação |
| empenhado / liquidado / pago | Estágios da despesa (R$) |

## Conjunto B — `despesas_por_instituicao.*` (por órgão do MEC)
Endpoint `/despesas/por-orgao`, órgão superior 26000 (Ministério da Educação).
Cada linha é o TOTAL do órgão no ano (todas as funções). Para universidades e
institutos federais a despesa é majoritariamente ensino superior, mas não é
estritamente a subfunção 364 — use o Conjunto A para precisão de subfunção.

| Coluna | Descrição |
|--------|-----------|
| ano | Ano do exercício |
| codigoOrgaoSuperior / orgaoSuperior | Sempre 26000 / Ministério da Educação |
| codigoOrgao / orgao | Instituição (universidade, IF, hospital, fundo...) |
| tipo_instituicao | Categoria derivada para comparação entre pares |
| chave_serie | Série temporal: código do órgão |
| empenhado / liquidado / pago | Estágios da despesa (R$) |

## Variáveis derivadas (ambos os conjuntos)
| Coluna | Descrição |
|--------|-----------|
| taxa_liquidacao | liquidado / empenhado |
| taxa_pagamento | pago / empenhado |
| valor_a_liquidar | empenhado - liquidado |
| restos_a_pagar | liquidado - pago |
| variacao_pago_aa | Variação % do pago vs. ano anterior (por série) |
| zscore_pago | z-score do pago no histórico da série |
| zscore_robusto_pago | z-score robusto (mediana/MAD) do pago |
| zscore_pago_entre_pares | (só B) z-score do pago entre instituições do mesmo tipo, no mesmo ano |
| flag_pago_maior_empenhado | Incoerência: pago > empenhado |
| flag_liquidado_maior_empenhado | Incoerência: liquidado > empenhado |
| flag_valor_negativo | Algum valor negativo |
| flag_anomalia_zscore | \|zscore_pago\| > 3 |
| flag_anomalia_robusto | \|zscore_robusto_pago\| > 3,5 |
| flag_salto_anual | \|variacao_pago_aa\| > 100% |
| flag_atipico_entre_pares | (só B) \|zscore_pago_entre_pares\| > 3 |
| flag_anomalia | Consolidação (OU lógico) de todas as flags acima |

## Sugestões para detecção de anomalias
- Modelos não supervisionados (Isolation Forest, LOF, DBSCAN) sobre
  `[empenhado, liquidado, pago, taxa_pagamento, variacao_pago_aa, zscore_pago]`.
- No Conjunto B, `zscore_pago_entre_pares` compara cada instituição aos pares
  do mesmo tipo — bom para achar instituições fora do padrão em um dado ano.
- As colunas `flag_*` servem como regras de negócio e rótulos fracos para
  validar os modelos não supervisionados.

## Conjuntos derivados da Fase 1 (qualidade, deflação, ano parcial)

As tabelas acima descrevem `despesas_ensino_superior.*` e
`despesas_por_instituicao.*` — a saída original de `coletar_despesas.py`
(tarefa 0.1). A Fase 1 do ROADMAP adiciona dois conjuntos derivados, cada
um em cima do anterior. **Use `*_v2` para qualquer análise de anomalia — os
dois primeiros existem apenas como estágios intermediários do pipeline.**

### `*_real.{csv,parquet}` (tarefa 1.2 — `analises/01b_deflacionar.py`)
Mesmas colunas de A/B, mais `empenhado_real`, `liquidado_real`, `pago_real`:
valores deflacionados pelo IPCA (fonte:
`dados/externos/ipca_anual.csv`, obtido por `analises/00_baixar_ipca.py`),
em R$ do último ano com os 12 meses de IPCA disponíveis (ano-base). As
colunas `taxa_*`/`zscore_*`/`flag_*` deste arquivo AINDA são as originais
(nominais, sem dedup, sem exclusão de ano parcial) — não usar para análise
de anomalia; servem só de estágio intermediário para a tarefa 1.3.

### `*_v2.{csv,parquet}` (tarefa 1.3 — `analises/01c_ano_parcial_e_flags.py`)
Conjunto recomendado para a Fase 2. Diferenças em relação ao `_real`:
- **Deduplicado** (Conjunto A): linhas de `(ano, chave_serie)` duplicadas
  por grafia divergente do mesmo programa/ação na fonte (ver
  `relatorios/01_qualidade.md`, seção 4) foram agregadas por soma.
- **`ano_parcial`** (bool): `True` no ano em que a coleta foi executada
  (detectado pelo carimbo de `dados/raw/*.json` —
  `sucuri.persistencia.detectar_ano_coleta`), tipicamente com exercício
  orçamentário incompleto.
- **`serie_curta`** (bool, só A): `True` para séries (`chave_serie`) com
  menos de 5 anos distintos de observação.
- `variacao_pago_aa`, `zscore_pago`, `zscore_robusto_pago` e (só B)
  `zscore_pago_entre_pares` foram **recalculados com base em `pago_real`**
  (não mais `pago` nominal) e **excluindo** da base estatística as linhas
  com `ano_parcial=True` ou `serie_curta=True`. Essas linhas ficam com
  `NaN` nas métricas e `False` nas flags derivadas — não são avaliadas
  quanto a anomalia por falta de uma base de comparação confiável (mas
  `empenhado`/`liquidado`/`pago`/`*_real` continuam preenchidos
  normalmente).
- `flag_anomalia` foi recalculada por `consolidar_flags` sobre o conjunto
  final de flags acima.
