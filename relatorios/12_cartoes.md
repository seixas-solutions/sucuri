# Cartão de Pagamento do Governo Federal (CPGF) — tarefa 3.6

Gerado por `analises/12_cartoes.py`. Amostra: mesmas 15 instituições das
tarefas 3.2/3.3, transações de 2023 a 2025, CPGF (tipoCartao=1).
16380 transações brutas coletadas.

## 1. Limitações desta coleta

- **Detecção de saque:** o payload de `/cartoes` não tem campo explícito
  distinguindo saque de compra — a coluna `eh_provavel_saque` é uma
  heurística por nome do estabelecimento (contém "BANCO", "CAIXA ECON",
  "SAQUE" ou "CAIXA ELETRO"), não uma classificação oficial da fonte.
- **Possível truncamento na coleta do EBSERH:** a API retornou um erro
  HTTP 400 ("Erro ao executar a consulta") na página 175 da consulta do
  EBSERH — um erro genérico do servidor, não do cliente. O código de
  coleta (`sucuri.api.requisitar`/`coletar_paginado`) trata qualquer
  página que não retorne dados como "fim da paginação", **indistinguível
  de um erro transitório do servidor** — os 2.610 registros do EBSERH
  reportados abaixo (exatamente 174 páginas completas × 15) podem não ser
  o total real se houver mais páginas depois da 175. Não corrigido nesta
  tarefa; uma melhoria futura seria distinguir erro de fim-de-dados e
  tentar novamente daquele ponto.

## 2. Resumo de red flags por instituição

| orgao                                                                | n_transacoes   | valor_total   | n_fim_de_semana   | pct_fim_de_semana   | n_dezembro   | n_provavel_saque   | pct_provavel_saque   |
|:---------------------------------------------------------------------|:---------------|:--------------|:------------------|:--------------------|:-------------|:-------------------|:---------------------|
| Universidade Federal Fluminense                                      | 6583           | 3.173.496,92  | 67                | 1.0%                | 0            | 2                  | 0.0%                 |
| Empresa Brasileira de Serviços Hospitalares                          | 2610           | 1.986.385,87  | 12                | 0.5%                | 198          | 1                  | 0.0%                 |
| Instituto Federal de Educação, Ciência e Tecnologia do Maranhão      | 2049           | 1.180.318,41  | 40                | 2.0%                | 40           | 0                  | 0.0%                 |
| Hospital de Clínicas de Porto Alegre                                 | 2662           | 882.529,99    | 26                | 1.0%                | 218          | 0                  | 0.0%                 |
| Universidade Federal de Minas Gerais                                 | 902            | 353.561,72    | 2                 | 0.2%                | 0            | 0                  | 0.0%                 |
| Instituto Federal de Educação, Ciência e Tecnologia de São Paulo     | 312            | 213.164,94    | 6                 | 1.9%                | 7            | 0                  | 0.0%                 |
| Universidade Federal do Rio de Janeiro                               | 247            | 110.145,08    | 1                 | 0.4%                | 14           | 0                  | 0.0%                 |
| Universidade Federal do Estado do Rio de Janeiro                     | 358            | 93.041,25     | 0                 | 0.0%                | 14           | 0                  | 0.0%                 |
| Instituto Federal de Educação, Ciência e Tecnologia do Ceará         | 167            | 82.915,69     | 0                 | 0.0%                | 14           | 0                  | 0.0%                 |
| Universidade Federal do Rio Grande                                   | 378            | 45.511,40     | 3                 | 0.8%                | 0            | 0                  | 0.0%                 |
| Universidade Federal do Triângulo Mineiro                            | 110            | 24.740,79     | 0                 | 0.0%                | 7            | 0                  | 0.0%                 |
| Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior | 1              | 377,30        | 0                 | 0.0%                | 0            | 0                  | 0.0%                 |
| Universidade Federal do Delta do Parnaíba                            | 1              | 220,00        | 0                 | 0.0%                | 0            | 0                  | 0.0%                 |

**Leitura:** 157 transações em fim de semana e 512 em dezembro no
total da amostra — datas atípicas para despesa administrativa rotineira
(não em si prova de irregularidade: viagens a serviço, eventos, plantões
de unidades de saúde como o Hospital de Clínicas legitimamente geram
gasto fora do horário comercial). 3 transações classificadas como
provável saque pela heurística acima.

## 3. Valores repetidos pelo mesmo portador (≥3 ocorrências)

| portadorCpf    | portadorNome                 | orgao                                                           | valor    | n_ocorrencias   |
|:---------------|:-----------------------------|:----------------------------------------------------------------|:---------|:----------------|
| ***.337.410-** | PAULO CESAR HUCKEMBECK NUNES | Hospital de Clínicas de Porto Alegre                            | 600,00   | 21              |
| ***.896.320-** | ALESSANDRO CAMARGO DA SILVA  | Hospital de Clínicas de Porto Alegre                            | 800,00   | 20              |
| ***.784.473-** | ANNATANAEL SILVA PAIVA       | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 1.000,00 | 17              |
| ***.632.073-** | EMISVALDO PEREIRA DA SILVA   | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 1.000,00 | 15              |
| ***.115.480-** | FELIPE DALBOSCO SILVEIRA     | Hospital de Clínicas de Porto Alegre                            | 600,00   | 14              |
| ***.115.480-** | FELIPE DALBOSCO SILVEIRA     | Hospital de Clínicas de Porto Alegre                            | 400,00   | 13              |
| ***.779.923-** | MICHEL DA SILVA REIS         | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 800,00   | 12              |
| ***.166.420-** | MOISES MOREIRA PINHEIRO      | Hospital de Clínicas de Porto Alegre                            | 800,00   | 11              |
| ***.084.830-** | LUIZ HENRIQUE STEIN          | Hospital de Clínicas de Porto Alegre                            | 600,00   | 10              |
| ***.409.857-** | JESSIKA FIGUEREDO ALVES      | Universidade Federal Fluminense                                 | 2.800,00 | 8               |
| ***.783.990-** | BRENDA SOUSA FERREIRA        | Hospital de Clínicas de Porto Alegre                            | 800,00   | 7               |
| ***.765.573-** | WALDIR BATISTA SERRA         | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 50,00    | 7               |
| ***.053.457-** | RAFAEL DUARTE XAVIER         | Universidade Federal Fluminense                                 | 15,00    | 7               |
| ***.314.824-** | BRUNO ALYSSON SOUZA VALENTIM | Empresa Brasileira de Serviços Hospitalares                     | 2.500,00 | 7               |
| ***.783.990-** | BRENDA SOUSA FERREIRA        | Hospital de Clínicas de Porto Alegre                            | 799,68   | 6               |
| ***.765.573-** | WALDIR BATISTA SERRA         | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 350,00   | 6               |
| ***.765.573-** | WALDIR BATISTA SERRA         | Instituto Federal de Educação, Ciência e Tecnologia do Maranhão | 100,00   | 6               |
| ***.723.320-** | RODRIGO LARANJO DE FREITAS   | Universidade Federal do Rio Grande                              | 40,00    | 6               |
| ***.931.054-** | FERNANDO FREITAS DE MEDEIROS | Empresa Brasileira de Serviços Hospitalares                     | 43,42    | 6               |
| ***.171.220-** | VIVIAN SPESSATTO             | Hospital de Clínicas de Porto Alegre                            | 226,44   | 5               |

**Leitura:** o mesmo portador com o mesmo valor exato repetido várias
vezes pode ser uma despesa recorrente legítima (ex.: assinatura mensal,
combustível com preço estável) ou um padrão a checar manualmente —
regra aqui é puramente descritiva, sem limiar de valor associado (ao
contrário do fracionamento de contratos, o CPGF não tem um teto de
dispensa formalmente análogo disponível nesta fonte).

Os dois primeiros casos (21× e 20×, ambos no Hospital de Clínicas de Porto
Alegre) têm frequência muito próxima de mensal ao longo dos ~35 meses da
janela de coleta (2023–2025) — leitura mais provável: pagamento fixo
recorrente (ex.: plantão, ajuda de custo mensal), não fracionamento de
despesa pontual. Casos com poucas ocorrências (5–8×) espalhadas de forma
menos regular no tempo são candidatos mais interessantes para checagem
manual do que os de maior contagem.

## 4. Dados salvos

`dados/cpgf_mec.parquet` — uma linha por transação coletada.
