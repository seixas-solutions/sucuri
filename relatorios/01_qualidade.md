# Relatório de qualidade dos dados — tarefa 1.1

Gerado por `analises/01_qualidade.py` em 2026-07-16 20:34.
Escopo: Conjunto A (`despesas_ensino_superior`) e Conjunto B
(`despesas_por_instituicao`), tal como salvos por `coletar_despesas.py`
(sem deflação nem tratamento de ano parcial — isso é feito nas tarefas 1.2
e 1.3). Este relatório verifica **qualidade dos dados**, não anomalias de
gasto.

## 1. Cobertura por ano

### Conjunto A — funcional-programático

|   ano |   n_linhas |   n_series |   total_pago_bi |
|------:|-----------:|-----------:|----------------:|
|  2014 |        175 |        161 |          25.89  |
|  2015 |        162 |        149 |          29.642 |
|  2016 |        156 |        145 |          29.535 |
|  2017 |        113 |        108 |          30.677 |
|  2018 |        102 |         97 |          29.646 |
|  2019 |        109 |         88 |          30.408 |
|  2020 |         74 |         74 |          29.107 |
|  2021 |         70 |         70 |          28.815 |
|  2022 |         62 |         62 |          30.431 |
|  2023 |         61 |         61 |          33.884 |
|  2024 |         83 |         83 |          35.198 |
|  2025 |         77 |         77 |          41.078 |
|  2026 |         74 |         74 |          21.071 |

### Conjunto B — por instituição (MEC)

|   ano |   n_linhas |   n_series |   total_pago_bi |
|------:|-----------:|-----------:|----------------:|
|  2014 |        111 |        111 |         104.711 |
|  2015 |        111 |        111 |         112.718 |
|  2016 |        111 |        111 |         120.604 |
|  2017 |        111 |        111 |         129.591 |
|  2018 |        111 |        111 |         123.526 |
|  2019 |        111 |        111 |         122.892 |
|  2020 |        116 |        116 |         117.361 |
|  2021 |        117 |        117 |         126.744 |
|  2022 |        117 |        117 |         143.22  |
|  2023 |        117 |        117 |         165.972 |
|  2024 |        117 |        117 |         176.908 |
|  2025 |        117 |        117 |         204.737 |
|  2026 |        117 |        117 |         114.569 |

**Leitura:** 2026 aparece com poucos meses de dados (coleta feita em
julho/2026) — é o **ano parcial** já documentado em `CLAUDE.md`; seu
`total_pago_bi` mais baixo não indica queda de despesa, apenas cobertura
incompleta do exercício. Tratado formalmente na tarefa 1.3.

## 2. Proporção de zeros por coluna monetária

### Conjunto A

| coluna    |   pct_zeros |
|:----------|------------:|
| empenhado |        78.8 |
| liquidado |        81.1 |
| pago      |        81.2 |

### Conjunto B

| coluna    |   pct_zeros |
|:----------|------------:|
| empenhado |           0 |
| liquidado |           0 |
| pago      |           0 |

**Leitura:** o Conjunto A tem proporção de zeros muito mais alta que o B —
esperado, pois A tem granularidade fina (programa × ação), com muitas
combinações que só recebem dotação/execução em alguns anos. Linhas
zeradas não são erro: representam ações orçamentárias existentes sem
execução naquele ano. Confirma a ressalva já registrada em `CLAUDE.md`
("mediana de empenhado/liquidado/pago é zero" no Conjunto A).

## 3. Séries curtas (Conjunto A)

125 de 239 séries (52.3%) têm menos de 5 anos de observações.

Séries com poucos anos de histórico tornam `zscore_pago`/`variacao_pago_aa`
pouco confiáveis (poucos pontos para estimar média/desvio). A tarefa 1.3
cria a flag `serie_curta` para essas 125 séries e as trata à parte na
Fase 2.

## 4. Duplicatas

- Conjunto A: 69 linhas duplicadas em (`ano`, `chave_serie`) — em
  69 grupos ano×série com 2 linhas cada.
- Conjunto B: 0 linhas duplicadas em (`ano`, `chave_serie`).

**Causa-raiz investigada (Conjunto A):** não são séries diferentes
colidindo por acaso — é a API retornando, para o **mesmo**
`codigoPrograma`/`codigoAcao`, duas grafias do nome do programa/ação (ex.:
"BRASIL UNIVERSITARIO" vs. "BRASIL UNIVERSITÁRIO", "BOLSA PERMANENCIA" vs.
"BOLSAPERMANENCIA" sem espaço), aparentemente por uma correção de texto na
fonte que não substituiu o registro antigo. Em **67
de 69** grupos os dois registros têm valores monetários
idênticos (frequentemente ambos zero); em **2
de 69** grupos os valores diferem — um registro carrega o
valor real e o outro fica zerado. Exemplo:

| ano   | programa                                                                  | acao                                              | empenhado     | liquidado     | pago          |
|:------|:--------------------------------------------------------------------------|:--------------------------------------------------|:--------------|:--------------|:--------------|
| 2014  | EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | CONCESSAO DE BOLSA PERMANENCIA NO ENSINO SUPERIOR | 77,500,700.00 | 77,376,300.00 | 77,366,700.00 |
| 2014  | EDUCACAO SUPERIOR - GRADUACAO, POS-GRADUACAO, ENSINO, PESQUISA E EXTENSAO | CONCESSAO DE BOLSAPERMANENCIA NO ENSINO SUPERIOR  | 0.00          | 0.00          | 0.00          |

**Risco:** se `chave_serie` (programa-ação) for tratada como identificador
único de série sem agregação, os `2` casos
com valores divergentes fazem uma série real "sumir" em anos em que a API
devolveu a grafia zerada, e "reaparecer" no ano seguinte — parecendo (para um
detector de anomalia ingênuo) um salto de 0 para um valor alto, quando na
verdade não houve salto algum, apenas duas grafias do mesmo registro. Fixado
na tarefa 1.3: os dois conjuntos passam por agregação
`groupby(["ano","chave_serie"]).sum()` nas colunas monetárias antes do
recálculo de flags, eliminando a duplicidade sem perder valor.

## 5. Incoerências de execução orçamentária

Linhas em que os estágios da despesa (empenhado → liquidado → pago) não
seguem a ordem esperada. Podem refletir estornos, republicações ou
particularidades contábeis legítimas — não são necessariamente erro de
dado, mas merecem checagem manual quando poucas.

### Conjunto A (1 com pago > empenhado, 0 com valor negativo)

**`flag_pago_maior_empenhado`** (pago > empenhado):

| ano   | programa                                                              | acao                                                                                                    | empenhado   | liquidado   | pago       |
|:------|:----------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------|:------------|:------------|:-----------|
| 2026  | EDUCACAO SUPERIOR: QUALIDADE, DEMOCRACIA, EQUIDADE E SUSTENTABILIDADE | REGULACAO E SUPERVISAO DOS CURSOS DE GRADUACAO E DE INSTITUICOES PUBLICAS E PRIVADAS DE ENSINO SUPERIOR | 67.00       | 103,240.00  | 103,240.00 |

**`flag_valor_negativo`**: nenhuma linha.

### Conjunto B (0 com pago > empenhado, 0 com valor negativo)

**`flag_pago_maior_empenhado`**: nenhuma linha.

**`flag_valor_negativo`**: nenhuma linha.

## 6. Checagem descritiva de ordem de grandeza

Comparação **qualitativa**, não uma validação formal (essa é a tarefa 4.2,
contra dotação do SIOP/LOA): o total pago em 2025 no Conjunto B (todos os
órgãos do MEC, todas as funções) foi de aproximadamente **R$ 204.7
bilhões**, e no Conjunto A (só subfunção 364 — Ensino Superior, nível
federal) foi de aproximadamente **R$ 41.1 bilhões**. Ambos os
valores estão na ordem de grandeza publicamente conhecida do orçamento
federal do MEC (dezenas de bilhões de reais/ano, historicamente entre
~R$100 bi e ~R$200 bi de orçamento total do ministério, do qual uma fração
relevante é ensino superior). Não há, portanto, indício de erro grosseiro de
unidade (ex.: valores em centavos não convertidos, ou truncamento). Uma
comparação linha a linha com a dotação autorizada fica para a tarefa 4.2.

## 7. Conclusão

Não há erro de ordem de grandeza. Três pontos exigem tratamento antes da
modelagem de anomalias (Fase 2), todos endereçados na tarefa 1.3:

1. **Ano parcial** (seção 1) — já antecipado em `CLAUDE.md`.
2. **Séries curtas** (seção 3) — já antecipado em `CLAUDE.md`.
3. **Duplicatas por grafia no Conjunto A** (seção 4) — achado **novo** desta
   tarefa, não estava em `CLAUDE.md` antes deste relatório. É a descoberta
   mais importante desta análise de qualidade: sem a agregação por
   `(ano, chave_serie)`, a Fase 2 correria risco real de gerar falsos
   positivos de "salto anual" a partir de uma duplicidade de texto na fonte,
   não de um evento de gasto.

As incoerências da seção 5, quando existentes, devem ser lidas como
candidatas a checagem manual, não como conclusão de erro.
