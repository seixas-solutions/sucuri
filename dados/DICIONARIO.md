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
