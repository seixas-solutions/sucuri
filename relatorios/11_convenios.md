# Convênios e transferências — tarefa 3.5

Gerado por `analises/11_convenios.py`. Concedente: Ministério da Educação
e órgãos vinculados (FNDE, CAPES etc., capturados automaticamente por
`codigoOrgao=26000`), 01/01/2018 a 31/12/2025.
4537 convênios brutos coletados.

## 1. Top 20 convenentes por valor total, com status de prestação de contas

| convenenteCnpjCpf   | convenenteNome                                | convenenteTipo                                        | localidadeTipo   | valor_total   | n_convenios   | n_inadimplentes   |
|:--------------------|:----------------------------------------------|:------------------------------------------------------|:-----------------|:--------------|:--------------|:------------------|
| 04.312.419/0001-30  | SECRETARIA DE ESTADO DE EDUCACAO E DESPORTO E | Administração Pública Estadual ou do Distrito Federal | Estadual         | 51.484.537,84 | 13            | 0                 |
| 00.278.912/0001-20  | FUNDACAO DE APOIO A EDUCACAO E DESENVOLVIMENT | Entidades Sem Fins Lucrativos                         | Municipal        | 45.480.710,01 | 6             | 0                 |
| 08.469.280/0001-93  | FUNDACAO NORTE RIO GRANDENSE DE PESQUISA E CU | Entidades Sem Fins Lucrativos                         | Municipal        | 39.490.411,20 | 1             | 0                 |
| 03.736.617/0001-68  | ORGANIZACAO DAS NACOES UNIDAS PARA EDUCACAO,  | Organizações Internacionais                           | Municipal        | 25.450.004,60 | 2             | 0                 |
| 42.498.659/0001-60  | SECRETARIA DE ESTADO DE EDUCACAO              | Administração Pública Estadual ou do Distrito Federal | Estadual         | 24.428.545,76 | 2             | 0                 |
| 08.241.804/0001-94  | SECRETARIA DE ESTADO DA EDUCACAO, DA CULTURA, | Administração Pública Estadual ou do Distrito Federal | Estadual         | 22.864.585,76 | 12            | 0                 |
| 02.585.924/0001-22  | SECRETARIA DE ESTADO DE EDUCACAO DE MATO GROS | Administração Pública Estadual ou do Distrito Federal | Estadual         | 19.417.745,68 | 16            | 0                 |
| 03.658.432/0001-82  | GEAP AUTOGESTAO EM SAUDE                      | Entidades Sem Fins Lucrativos                         | Municipal        | 17.299.609,00 | 2             | 0                 |
| 84.306.588/0001-04  | MUNICIPIO DE EPITACIOLANDIA                   | Administração Pública Municipal                       | Municipal        | 15.108.231,65 | 3             | 0                 |
| 03.352.086/0001-00  | ESTADO DO MARANHAO - SECRETARIA DE ESTADO DA  | Administração Pública Estadual ou do Distrito Federal | Estadual         | 14.971.838,19 | 9             | 0                 |
| 03.604.410/0001-30  | UNIAO NACIONAL DOS DIRIGENTES MUNICIPAIS DE E | Entidades Sem Fins Lucrativos                         | Municipal        | 13.642.753,21 | 3             | 0                 |
| 00.394.601/0001-26  | DISTRITO FEDERAL                              | Administração Pública Estadual ou do Distrito Federal | Estadual         | 12.382.442,31 | 1             | 0                 |
| 11.022.597/0001-91  | FUNDACAO UNIVERSIDADE DE PERNAMBUCO           | Administração Pública Estadual ou do Distrito Federal | Estadual         | 12.079.002,66 | 2             | 0                 |
| 00.394.676/0001-07  | SECRETARIA DE ESTADO DE EDUCACAO DO DISTRITO  | Administração Pública Estadual ou do Distrito Federal | Estadual         | 11.815.971,23 | 5             | 0                 |
| 34.670.976/0001-93  | MUNICIPIO DE CUMARU DO NORTE                  | Administração Pública Municipal                       | Municipal        | 11.702.858,99 | 3             | 0                 |
| 04.280.196/0001-76  | UNIVERSIDADE DO ESTADO DO AMAZONAS            | Administração Pública Estadual ou do Distrito Federal | Estadual         | 10.570.058,97 | 2             | 0                 |
| 06.307.102/0001-30  | MUNICIPIO DE SAO LUIS                         | Administração Pública Municipal                       | Municipal        | 10.282.818,60 | 6             | 0                 |
| 03.438.229/0001-09  | FUNDACAO EUCLIDES DA CUNHA DE APOIO INSTITUCI | Entidades Sem Fins Lucrativos                         | Municipal        | 8.322.668,63  | 1             | 0                 |
| 04.033.254/0001-67  | SECRETARIA DE ESTADO DA EDUCACAO, CULTURA E E | Administração Pública Estadual ou do Distrito Federal | Estadual         | 8.265.726,04  | 12            | 0                 |
| 80.257.355/0001-08  | UNIVERSIDADE ESTADUAL DE PONTA GROSSA         | Administração Pública Estadual ou do Distrito Federal | Estadual         | 7.930.492,28  | 11            | 0                 |

`n_inadimplentes` conta quantos dos convênios do próprio convenente estão
com situação "INADIMPLENTE" (qualquer variante do texto) — não é um
julgamento sobre o convenente como um todo, é a contagem literal de
convênios problemáticos.

## 2. Convenentes com múltiplos convênios inadimplentes (≥2)

_Nenhum convenente com ≥2 convênios inadimplentes na amostra._

## 3. Panorama geral

- 5 de 4537 convênios (0.1%) estão
  com situação inadimplente.
- Convenentes municipais: top 10 por valor concentram
  21.1% do total liberado a convenentes
  municipais — sinal de concentração a cruzar com o porte populacional dos
  municípios (fora do escopo desta tarefa).

**Vocabulário de `situacao` conferido integralmente** (não só a palavra
"INADIMPLENTE"): CONCLUÍDO (n=3590); ADIMPLENTE (n=878); ARQUIVADO (n=46); EM EXECUÇÃO (n=10); INADIMPLÊNCIA SUSPENSA (n=7); INADIMPLENTE (n=5); AGUARDANDO PRESTAÇÃO DE CONTAS (n=1). Duas categorias próximas foram
deliberadamente **excluídas** da contagem de inadimplência por não
significarem inadimplência atual — "INADIMPLÊNCIA SUSPENSA" (a pendência
foi suspensa/resolvida) e "AGUARDANDO PRESTAÇÃO DE CONTAS" (prazo ainda
não vencido, não é atraso).

**Achado a cruzar com as tarefas 3.2/3.3:** a "Fundação Euclides da Cunha
de Apoio Institucional à UFF" — já apontada nas tarefas 3.2 (86,6% do
valor contratado da UFF, HHI mais alto da amostra) e 3.3 (padrão de
fracionamento, 6 dispensas somando R$ 172.030,00) — também recebeu
R$ 8.322.668,63 em convênio do MEC/FNDE/CAPES no período, situação
"CONCLUÍDO" (sem inadimplência registrada aqui). É a terceira tarefa
consecutiva em que essa entidade aparece como caso atípico por um critério
diferente — reforça a prioridade de investigação específica desta
fundação de apoio na Fase 4 (achados públicos do TCU/CGU), não como
acusação, mas como convergência de múltiplos sinais independentes.

## 4. Dados salvos

`dados/convenios_mec.parquet` — um registro por convênio coletado.
