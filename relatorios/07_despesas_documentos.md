# Despesas por documento (visão híbrida órgão × subfunção) — tarefa 3.1

Gerado por `analises/07_despesas_documentos.py`. Piloto: **Universidade Federal de Ouro Preto**
(UG 154046, codigoOrgao 26277 no Conjunto B),
01/05/2025 a 31/05/2025 (31 dias
× 3 fases = até 93 requisições).

## 1. Limitações empíricas descobertas nesta tarefa

O endpoint `/despesas/documentos` é o único caminho via API para cruzar
**órgão** e **subfunção** ao mesmo tempo (nem `/despesas/por-orgao` nem
`/despesas/por-funcional-programatica`, usados desde a Fase 0, fazem esse
cruzamento). Duas limitações não óbvias a partir do Swagger, descobertas
tentando a API de verdade:

1. **Um dia por requisição.** O parâmetro `dataEmissao` não aceita
   intervalo — cobrir um ano inteiro de uma instituição custa até
   365 × 3 = 1.095 requisições. A ~90 req/min, isso é ≥12 minutos por
   instituição só nessa consulta.
2. **Filtra por Unidade Gestora (UG), não por `codigoOrgao`.** A UG é um
   código SIAFI de 6 dígitos, diferente do código de órgão de 5 dígitos
   usado em todo o resto deste projeto (`codigoOrgao=26277` para esta
   universidade, mas `unidadeGestora=154046`) — **não há endpoint público
   nesta API para converter um no outro**; `/orgaos-siafi` só resolve
   `codigoOrgao`. O código UG piloto usado aqui foi encontrado por tentativa
   (não por documentação). Escalar esta tarefa para outras instituições
   exige uma tabela `codigoOrgao → codigoUg`, que só existe nos arquivos
   de download em lote do portal (EXTERNAL.md, item E2) — **trabalho para
   rodar externamente**, não coberto por esta tarefa.

Por isso o piloto ficou deliberadamente pequeno: 1 instituição, 1 mês —
suficiente para provar que o mecanismo funciona (o documento individual
já vem com `funcao`/`subfuncao`/`codigoOrgao`, então o cruzamento
órgão×subfunção É possível), não para replicar o total anual do Conjunto A.

## 2. Coleta

837 documentos brutos coletados (todas as fases). Resumo
por fase:

| fase       | n_documentos   | valor_total   |
|:-----------|:---------------|:--------------|
| Empenho    | 17             | 543.412,99    |
| Liquidação | 274            | 0,00          |
| Pagamento  | 546            | 55.346.562,50 |

**Nota sobre a fase Liquidação:** valor total R$ 0,00 não é erro de
parsing — os 274 documentos dessa fase têm literalmente `valor="-"` na
resposta da API (junto com `especie="Não se aplica"`), isto é, a própria
API não reporta um valor monetário para o estágio de liquidação neste
endpoint. `sucuri.utils.brl_para_float` já trata `"-"` como 0,0
(ver `tests/test_utils.py`).

## 3. Validação: proporção da subfunção 364 no total de pagamentos do mês

| codigo_subfuncao   | subfuncao                                  | n_documentos   | valor_total   |
|:-------------------|:-------------------------------------------|:---------------|:--------------|
| 364                | 364 - Ensino superior                      | 456            | 27.291.501,14 |
| 272                | 272 - Previdência do regime estatutário    | 27             | 11.026.610,25 |
| -14                | -14 - Múltiplo                             | 15             | 10.901.281,97 |
| 846                | 846 - Outros encargos especiais            | 3              | 6.064.164,05  |
| 128                | 128 - Formação de recursos humanos         | 2              | 36.000,00     |
| 331                | 331 - Proteção e benefícios ao trabalhador | 3              | 24.627,62     |
| Sem informaç       | Sem informaç                               | 34             | 2.348,20      |
| 368                | 368 - Educação básica                      | 6              | 29,27         |

**Leitura:** dos pagamentos de Universidade Federal de Ouro Preto em 05/2025,
R$ 27.291.501,14 (49.3% do total do mês, R$ 55.346.562,50)
foram classificados na subfunção 364 (Ensino Superior) — o restante é
folha de pessoal, custeio administrativo e outras subfunções não
relacionadas a ensino superior especificamente, mesmo sendo uma
universidade. Isso é consistente com a lógica dos dois conjuntos usados
desde a Fase 0: o Conjunto B (por órgão) soma TODAS as subfunções da
instituição, e só uma fração é subfunção 364 — exatamente por isso o
Conjunto A (por subfunção) existe como painel separado. **Validação
alcançada nesta tarefa: o cruzamento órgão×subfunção funciona e produz
uma fração plausível (bem menor que 100%, coerente com a natureza mista
do orçamento de uma universidade)** — não uma comparação numérica direta
com o total anual do Conjunto A, que exigiria a coleta em escala (fora do
escopo desta tarefa; ver seção 1).

## 4. Dados salvos

`dados/despesas_univ_piloto_364.parquet` — todos os documentos coletados
(não só subfunção 364), com a coluna `eh_ensino_superior` marcando os que
são. Bruto salvo em `dados/raw/despesas_univ_piloto_raw_*.json`.
