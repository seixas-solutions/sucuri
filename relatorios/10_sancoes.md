# Sanções: CEIS, CNEP e acordos de leniência — tarefa 3.4

Gerado por `analises/10_sancoes.py`. 184 CNPJs de
fornecedores consultados (os que somam 80% do valor
total contratado em `dados/contratos_mec.parquet`) × 3 fontes (CEIS, CNEP,
acordos de leniência) = até 552 requisições.
123 registros de sanção brutos encontrados (antes de
qualquer filtro).

## 1. Por que consulta direcionada, não a base completa

CEIS, CNEP e acordos de leniência são registros **nacionais**, não
filtráveis por órgão — abrangem todo o setor público, não só o MEC. Uma
sondagem de paginação encontrou o CEIS ainda com páginas cheias na página
800 (12.000+ registros só nesse cadastro) — baixar a base inteira para
depois cruzar seria uma coleta de escala muito maior que este piloto.
Consultar por CNPJ direcionado é mais barato E mais preciso: só interessam
sanções de empresas que **já são fornecedoras do MEC**, e essas já estão
listadas em `contratos_mec.parquet`.

## 2. Sanções encontradas entre os fornecedores consultados

| fonte   |   n_registros |
|:--------|--------------:|
| ceis    |           119 |
| cnep    |             4 |

## 3. Contratos assinados com fornecedor já sancionado na data da assinatura

Cruzamento: fornecedor do contrato aparece em CEIS/CNEP/acordos de
leniência **com o período de sanção cobrindo a data de assinatura do
contrato** (não apenas "tem alguma sanção em algum momento" — sanção
posterior ao contrato não é o mesmo sinal).

_Nenhum contrato assinado com fornecedor já sancionado na data da assinatura._

**Achado desta tarefa:** 27 CNPJs entre os consultados têm sanção registrada E contrato no período coletado (720 combinações contrato×sanção no total) — mas em **nenhuma** delas a sanção começou antes ou durante a vigência da assinatura do contrato correspondente; todas as sanções encontradas começaram depois do contrato já assinado. Reportar só o número bruto (720) sem o filtro de data teria sido enganoso — pareceria um sinal forte quando, com a cronologia correta, não há nenhum caso de contratação com fornecedor já sancionado nesta amostra.

## 4. Dados salvos

`dados/sancoes.parquet` — todos os registros de sanção encontrados (não só
os cruzados com contratos). `dados/contratos_com_sancionados.csv` — o
cruzamento da seção 3 (pode estar vazio; o cruzamento roda de qualquer
forma, como pede o ROADMAP).

## 5. Limitação de escopo

Cobertura de 80% do valor contratado deixa de fora
fornecedores de contratos pequenos (que, individualmente, pesam pouco no
valor total, mas cuja ausência de checagem não deve ser lida como "sem
sanção" — apenas "não verificado nesta amostra"). Verificar os
demais fornecedores fica para o
usuário rodar externamente (ver EXTERNAL.md).
