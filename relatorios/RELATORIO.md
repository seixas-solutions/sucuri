# Relatório — Sucuri: Detecção de anomalias em despesas com Ensino Superior

**Fase reportada:** Fase 0 — Infraestrutura do projeto (ROADMAP.md, tarefas 0.1 e 0.2)
**Data:** 2026-07-16
**Responsável pela execução:** modelo de linguagem (Sonnet 5), seguindo CLAUDE.md e ROADMAP.md

---

## 1. Objetivo desta fase

A Fase 0 do ROADMAP não produz análises sobre as despesas em si — seu objetivo é
transformar o projeto de um único script (`coletar_despesas.py`) em uma base de
código reprodutível, testável e reutilizável pelas fases seguintes (qualidade
de dados, deflação, detecção de anomalias). Este relatório documenta **o que
foi feito**, não interpretações sobre os dados de despesas (essas começam na
Fase 1/2 e serão anexadas às próximas seções deste mesmo documento).

## 2. Tarefa 0.1 — Empacotamento e ambiente

### 2.1 Estrutura criada

```
pyproject.toml            # projeto gerenciado por uv (PEP 621 + hatchling)
uv.lock                   # lockfile de dependências
src/sucuri/
  __init__.py
  api.py                  # cliente da API do Portal da Transparência
  features.py             # engenharia de variáveis e construção dos painéis A/B
  persistencia.py         # salvamento de CSV/Parquet/JSON bruto e dicionário
  utils.py                # brl_para_float, razao_segura, classificar_instituicao
analises/                 # reservado para as fases 1–2 (vazio nesta fase)
relatorios/
  figuras/                # reservado para as fases 1–2 (vazio nesta fase)
  latex/                  # este relatório em LaTeX/PDF
tests/
  __init__.py
  test_utils.py
  test_features.py
coletar_despesas.py       # CLI fino: apenas argparse + orquestração, importa de sucuri.*
```

### 2.2 Migração de código

Toda a lógica reutilizável de `coletar_despesas.py` foi movida para o pacote
`src/sucuri/`, preservando exatamente o comportamento original (mesmos
parâmetros de API, mesmas fórmulas, mesmo formato de saída):

| Função/constante | Origem (script único) | Destino |
|---|---|---|
| `brl_para_float`, `_razao_segura`, `classificar_instituicao` | topo do script | `sucuri/utils.py` (renomeada para `razao_segura`, pública) |
| `carregar_chave_api`, `criar_sessao`, `requisitar`, `coletar_paginado`, `coletar_intervalo`, constantes de endpoint/rate limit | seção "Coleta genérica" | `sucuri/api.py` |
| `construir_df_funcional`, `construir_df_instituicao`, `_indicadores_execucao`, `_features_serie_temporal`, `_consolidar_flags` | seções (A)/(B) e "Engenharia de variáveis" | `sucuri/features.py` (funções internas tornadas públicas: `indicadores_execucao`, `features_serie_temporal`, `consolidar_flags`) |
| `salvar_dataset`, `escrever_dicionario`, `DICIONARIO`, `resumir` | seção "Persistência" | `sucuri/persistencia.py` |

O arquivo `coletar_despesas.py` (antes `coletar_despesas_ensino_superior.py`)
ficou reduzido a ~125 linhas: apenas `argparse`, orquestração das coletas (A) e
(B), e chamadas às funções do pacote. Nenhuma fórmula ou regra de negócio foi
alterada durante a migração — apenas reorganizada em módulos.

### 2.3 Dependências (`pyproject.toml`)

Gerenciadas por `uv`: `pandas`, `pyarrow`, `requests`, `python-dotenv`,
`scikit-learn`, `scipy`, `matplotlib` (produção); `ruff`, `pytest`
(grupo `dev`). `uv sync --group dev` cria o ambiente virtual e resolve o
lockfile em poucos segundos.

### 2.4 Verificação dos critérios de aceite

| Critério (ROADMAP 0.1) | Resultado |
|---|---|
| `uv run python coletar_despesas.py --help` funciona | ✅ Exibe o help completo, docstring preservada |
| `uv run pytest` roda (mesmo com 0 testes) | ✅ Rodou sem erros antes da tarefa 0.2 popular os testes |
| `uv run ruff check .` sem erros | ✅ `All checks passed!` |

## 3. Tarefa 0.2 — Testes unitários das funções críticas

### 3.1 Cobertura

37 testes em 2 arquivos, cobrindo exatamente as funções indicadas no ROADMAP:

**`tests/test_utils.py`** (23 testes)
- `brl_para_float`: formato brasileiro com separador de milhar (`1.059.473.395,24`),
  sem separador de milhar, `None`, string vazia, string só com espaços, valor já
  numérico (`int`/`float`), entrada inválida (`"abc"` → `NaN`), valor negativo.
- `razao_segura`: divisão normal e **denominador zero → `NaN`** (em vez de erro
  ou `inf`).
- `classificar_instituicao`: um caso por categoria (Universidade Federal,
  Hospitalar/EBSERH, Instituto Federal, CEFET, CAPES, Fundo FNDE/FIES, Educação
  Básica, Outros/Administração), mais `None` e string vazia.

**`tests/test_features.py`** (14 testes)
- `indicadores_execucao`: taxas e saldos em caso normal; **`empenhado == 0` →
  taxas `NaN` sem exceção**; disparo isolado de cada flag de incoerência
  (`pago > empenhado`, `liquidado > empenhado`, valor negativo); ausência de
  falso positivo em valores coerentes.
- `features_serie_temporal`: variação anual ano a ano; disparo de
  `flag_salto_anual` acima de 100%; **série com desvio-padrão zero (valores
  constantes) não gera erro de divisão por zero** e produz `zscore` `NaN` em
  vez de indefinido; série com uma única observação; independência entre
  séries diferentes agrupadas no mesmo DataFrame.
- `consolidar_flags`: nenhuma flag ativa, uma flag ativa, flag extra
  (`flag_atipico_entre_pares`) considerada, valores nulos tratados como
  `False` na consolidação.

Os dois casos de borda explicitamente pedidos no ROADMAP — **divisão por
zero** e **série com desvio-padrão zero** — estão cobertos e passam sem
exceções, confirmando que as fórmulas originais (`.replace(0, pd.NA)`) já
protegiam contra isso; os testes tornam essa garantia explícita e verificável
automaticamente.

### 3.2 Resultado da execução

```
uv run pytest -v
============================== 37 passed in 0.67s ==============================

uv run ruff check .
All checks passed!
```

*Aceite (ROADMAP 0.2):* ✅ `uv run pytest` verde; as três funções citadas no
ROADMAP (`brl_para_float`/`classificar_instituicao`,
`_indicadores_execucao`, `_features_serie_temporal`, `_consolidar_flags`)
têm cobertura direta.

## 4. Validação de não regressão

Após a migração, foi confirmado por busca no repositório que não restou
nenhuma referência às funções privadas antigas (`_indicadores_execucao`,
`_features_serie_temporal`, `_consolidar_flags`, `_razao_segura`) fora do
pacote `sucuri`, e que os módulos migrados importam e executam corretamente
(`from sucuri.utils import ...`, `from sucuri.features import ...`, `from
sucuri.api import ...`). Os dados já coletados em `dados/` (dois conjuntos,
2014–2026) não foram alterados nesta fase — nenhuma recoleta foi executada.

## 5. Ressalvas e decisões registradas

- As funções antes privadas (`_indicadores_execucao` etc.) foram tornadas
  públicas (sem `_`) ao mover para `sucuri/features.py`, pois passam a ser a
  API pública do pacote reutilizada pelas fases seguintes. Isso é uma mudança
  de visibilidade, não de comportamento.
- `analises/` e `relatorios/figuras/` foram criados vazios nesta fase — serão
  populados a partir da Fase 1/2 do ROADMAP.
- Nenhum dado foi recoletado; a chave `GOVBR_API_KEY` não foi lida nem
  impressa durante esta fase (apenas os testes unitários, que não fazem
  chamadas de rede, foram executados).

## 6. Estado do ROADMAP

Tarefas 0.1 e 0.2 marcadas como concluídas em `ROADMAP.md`. Próxima tarefa
pendente: **1.1 Relatório de qualidade dos dados** (`analises/01_qualidade.py`
→ `relatorios/01_qualidade.md`), que passa a ser a primeira seção deste
relatório a conter interpretação de dados reais de despesas.

---

## Instrução de manutenção deste relatório

A partir da Fase 1, toda nova tarefa do ROADMAP que gerar análise, medida
estatística ou modelo deve **acrescentar uma seção a este arquivo** (e à
versão LaTeX em `relatorios/latex/relatorios.tex`) com: o que foi medido, o
método usado, o resultado numérico e sua interpretação — nunca apenas o
código ou o caminho do arquivo gerado. Ver `CLAUDE.md`, seção "Registro de
análises e relatórios".
