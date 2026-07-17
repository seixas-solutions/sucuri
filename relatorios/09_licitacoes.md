# Licitações e compras — tarefa 3.3

Gerado por `analises/09_licitacoes.py`. Amostra: mesmas 15 instituições da
tarefa 3.2, licitações de 01/01/2024 a 31/12/2024.
1075 licitações brutas coletadas.

## 1. Limitação de escopo descoberta nesta tarefa

`/licitacoes` só aceita **até 1 mês por requisição** (diferente de
`/contratos`, que aceita o intervalo todo numa chamada) — descoberto por
erro HTTP 400 ("O período deve ser de no máximo 1 mês") ao tentar o mesmo
padrão da tarefa 3.2. Por isso a coleta ficou restrita a 2024 (1 ano, 12
requisições por instituição), não os 3 anos de `contratos_mec.parquet` —
o que limita a análise 3 abaixo (contratos sem licitação correspondente),
sujeita a falso positivo por essa diferença de cobertura temporal.

## 2. Licitações desertas/fracassadas repetidas (≥2 no mesmo órgão/ano)

_Nenhum órgão com ≥2 desertas/fracassadas na amostra._

**Leitura:** identificado por texto de `situacaoCompra` contendo "DESERTA"
ou "FRACASSAD" — deserta (nenhuma proposta) e fracassada (propostas
existiram mas nenhuma válida) têm causas distintas na prática, mas ambas
indicam uma tentativa de compra que não se concretizou; repetição no
mesmo órgão/ano é o sinal a olhar, não uma ocorrência isolada.

## 3. Indício de fracionamento (regra explícita)

Regra: ≥2 contratos por dispensa/inexigibilidade do mesmo (órgão,
fornecedor, ano), cada um abaixo de R$ 50.000,00
(limiar de referência do valor-base da Lei 14.133/2021, art. 75, inciso
II, para compras/serviços em geral — sujeito a atualização por decreto de
indexação não considerada aqui), cuja soma ultrapassa esse limiar.

| codigoOrgao   | orgao                                                            | fornecedorCnpjCpf   | fornecedorNome                                                                         | ano   | n_contratos   | valor_somado   |
|:--------------|:-----------------------------------------------------------------|:--------------------|:---------------------------------------------------------------------------------------|:------|:--------------|:---------------|
| 26236         | Universidade Federal Fluminense                                  | 03.438.229/0001-09  | FUNDACAO EUCLIDES DA CUNHA DE APOIO INSTITUCIONAL A UFF                                | 2023  | 6             | 172.030,00     |
| 26405         | Instituto Federal de Educação, Ciência e Tecnologia do Ceará     | 44.866.208/0001-63  | COOPESQUI COOPERATIVA DOS PRODUTORES RURAIS E PESCADORES DA REGIAO DOS INHAMUNS LTDA   | 2024  | 3             | 66.678,60      |
| 26439         | Instituto Federal de Educação, Ciência e Tecnologia de São Paulo | 10.568.281/0001-37  | COOPERATIVA DOS TRABALHADORES DA REFORMA AGRARIA TERRA LIVRE LTDA                      | 2023  | 3             | 55.016,80      |
| 26443         | Empresa Brasileira de Serviços Hospitalares                      | 03.606.427/0001-26  | FUJITECH EQUIPAMENTOS MEDICOS LTDA                                                     | 2023  | 2             | 90.950,00      |
| 26439         | Instituto Federal de Educação, Ciência e Tecnologia de São Paulo | 07.020.207/0001-77  | CODAFAVO COOPERATIVA DA AGRICULTURA FAMILIAR DE VOTUPORANGA                            | 2023  | 2             | 78.928,10      |
| 26443         | Empresa Brasileira de Serviços Hospitalares                      | 00.029.372/0003-02  | GE HEALTHCARE DO BRASIL COMERCIO E SERVICOS PARA EQUIPAMENTOS MEDICO-HOSPITALARES LTDA | 2024  | 2             | 66.922,57      |
| 26245         | Universidade Federal do Rio de Janeiro                           | 03.794.974/0001-82  | LAVANDERIA MILENIO LTDA                                                                | 2024  | 2             | 62.424,00      |
| 26443         | Empresa Brasileira de Serviços Hospitalares                      | 21.998.885/0001-30  | MEDIPHACOS INDUSTRIAS MEDICAS S/A                                                      | 2023  | 2             | 61.881,81      |

**Achado a cruzar com a tarefa 3.2:** a mesma "Fundação Euclides da Cunha
de Apoio Institucional à UFF" apontada na tarefa 3.2 como concentrando
86,6% do valor contratado da UFF (HHI 7.512, o mais alto da amostra)
aparece aqui também com 6 contratos por dispensa em 2023, cada um abaixo
do limiar, somando R$ 172.030,00 — a mesma entidade combina forte
concentração de valor E um padrão compatível com fracionamento. Não é
prova de irregularidade (fundações de apoio administram muitos pequenos
repasses de projetos legitimamente), mas é o tipo de sinal cruzado que a
Fase 4 (validação contra achados do TCU/CGU) deveria priorizar.

## 4. Contratos sem licitação correspondente

**Achado desta tarefa (corrigido):** o campo `numeroProcesso` no nível
raiz do payload de `/contratos` vem sempre "Sem informação" — o valor real
está aninhado em `compra.numeroProcesso` (não documentado no Swagger,
descoberto empiricamente; `sucuri.coletores.contratos` já foi corrigido
para usar o campo certo, com teste de regressão). Mesmo corrigido, apenas
3534 de 3534 contratos não-dispensa têm um número de
processo utilizável para o cruzamento (os demais têm o campo vazio mesmo
na fonte aninhada) — **é sobre esses 3534 que a comparação abaixo
é válida**, não sobre os 3534 totais.

3297 de 3534 contratos checáveis não têm `numeroProcesso`
correspondente entre as licitações coletadas no mesmo órgão.
**Ressalva forte:** dado que licitações só cobrem 2024 e contratos cobrem
2023–2025, boa parte dessas "ausências" é esperada por diferença de
janela temporal, não indício de irregularidade — esta análise é
estruturalmente inconclusiva no escopo desta tarefa piloto; uma coleta de
licitações cobrindo 2023–2025 completo (45 novas requisições por
instituição) resolveria isso, deixada para o usuário rodar externamente.

## 5. Dados salvos

`dados/licitacoes_mec.parquet` — uma linha por licitação coletada.
