# Contratos das instituições — tarefa 3.2

Gerado por `analises/08_contratos.py`. Amostra: 15
instituições do Conjunto B (estratificada por porte/tipo — ver script),
contratos vigentes entre 01/01/2023 e 31/12/2025.
4266 contratos brutos coletados.

## 1. Limitação de escopo desta tarefa

O ROADMAP original sugeria "anos 2018+"; um teste de paginação mostrou só
a UFRJ tendo 450+ contratos nesse intervalo — cobrir isso para uma amostra
de 15 órgãos custaria centenas de requisições. Optou-se por
2023–2025 (3 anos), amostra real e válida para a
análise de concentração de fornecedores, mas não o histórico completo.
Coleta mais longa (2018+, mais órgãos) fica para o usuário rodar
externamente — ver EXTERNAL.md.

## 2. Concentração de fornecedores (índice Herfindahl-Hirschman)

Escala 0–10.000 (soma dos market-shares percentuais ao quadrado, por
valor final de contrato). Referência de literatura antitruste: >2.500 é
convencionalmente "altamente concentrado" — usado aqui só como escala de
leitura, não como acusação (poucos fornecedores pode refletir mercado
naturalmente concentrado para o objeto contratado, ex.: obra
especializada).

| orgao                                                                |   codigoOrgao |   n_fornecedores |   hhi_fornecedores |
|:---------------------------------------------------------------------|--------------:|-----------------:|-------------------:|
| Universidade Federal Fluminense                                      |         26236 |               87 |               7512 |
| Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior |         26291 |               27 |               6138 |
| Universidade Federal de Rondonópolis                                 |         26454 |               15 |               2630 |
| Universidade Federal do Delta do Parnaíba                            |         26455 |                8 |               2419 |
| Universidade Federal do Estado do Rio de Janeiro                     |         26269 |               12 |               1854 |
| Universidade Federal de Minas Gerais                                 |         26238 |               64 |               1825 |
| Universidade Federal do Rio Grande                                   |         26273 |               15 |               1716 |
| Universidade Federal do Triângulo Mineiro                            |         26254 |               38 |               1683 |
| Universidade Federal do Agreste de Pernambuco                        |         26456 |               23 |               1677 |
| Universidade Federal do Rio de Janeiro                               |         26245 |              117 |               1070 |
| Instituto Federal de Educação, Ciência e Tecnologia do Maranhão      |         26408 |              152 |                586 |
| Instituto Federal de Educação, Ciência e Tecnologia de São Paulo     |         26439 |              326 |                548 |
| Empresa Brasileira de Serviços Hospitalares                          |         26443 |             1168 |                373 |
| Instituto Federal de Educação, Ciência e Tecnologia do Ceará         |         26405 |              223 |                305 |

### Decil superior de concentração (2 de 14 instituições, HHI ≥ 5086)

| orgao                                                                |   codigoOrgao |   n_fornecedores |   hhi_fornecedores |
|:---------------------------------------------------------------------|--------------:|-----------------:|-------------------:|
| Universidade Federal Fluminense                                      |         26236 |               87 |            7511.93 |
| Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior |         26291 |               27 |            6138.36 |

**Leitura do 1º colocado (UFF, HHI 7.512 apesar de 87 fornecedores
distintos):** o HHI pondera por valor, não por contagem — um único
fornecedor, a "Fundação Euclides da Cunha de Apoio Institucional à UFF",
concentra R$ 403,9 milhões dos R$ 466,5 milhões em contratos da UFF no
período (86,6%). Isso não é um fornecedor comercial comum: fundações de
apoio são entidades sem fins lucrativos que administram projetos de
pesquisa/extensão em nome da universidade — um arranjo comum e legal em
universidades federais brasileiras, não um indício automático de
irregularidade. Ainda assim, fundações de apoio já foram objeto de
apontamentos de auditoria do TCU em outras instituições por concentração
de contratação sem licitação — vale conferir a tarefa 3.3 (licitações) e,
na Fase 4, achados públicos do TCU/CGU especificamente sobre essa
fundação, antes de qualquer conclusão.

**Nota sobre instituição sem contratos nesta amostra:** Hospital de
Clínicas de Porto Alegre (`codigoOrgao=26294`, confirmado válido via
`/orgaos-siafi`) retornou 0 contratos em 2023–2025 — não investigado
nesta tarefa se é ausência real de contratos nesse período, publicação
sob outro código/canal (HCPA é sociedade de economia mista, regime de
contratação potencialmente distinto de universidades federais), ou
lacuna de dados. Fica como item em aberto, não como conclusão.

## 3. Dispensa e inexigibilidade de licitação

732 de 4266 contratos (17.2%) foram
contratados por dispensa ou inexigibilidade de licitação (identificado
pelo texto de `modalidadeCompra`) — modalidades legais, mas que dispensam
concorrência; proporção alta num órgão específico é sinal a cruzar com a
tarefa 3.3 (licitações) antes de qualquer leitura.

## 4. Termos aditivos

531 de 4266 contratos (12.4%) tiveram valor final maior que o inicial; aditivo médio nesses casos: 465.197,99 (54.6% do valor inicial, em média).

## 5. Dados salvos

`dados/contratos_mec.parquet` — um registro por contrato, com as colunas
derivadas (`valor_aditivado`, `pct_aditivado`, `prazo_dias`,
`eh_dispensa_ou_inexigibilidade`). Usado na tarefa 3.4 para cruzar
fornecedores com sanções (CEIS/CNEP).
