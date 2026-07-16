# Sucuri — Detecção de anomalias em despesas com Ensino Superior

## Propósito
Analisar despesas federais com Educação de Nível Superior extraídas da API do
Portal da Transparência (gov.br) e detectar anomalias/gastos atípicos, com
possibilidade de enriquecimento por outros conjuntos do próprio portal
(contratos, licitações, convênios, sanções etc.).

## Estrutura atual
```
pyproject.toml            # Projeto gerenciado por uv (dependências + dev: ruff, pytest)
coletar_despesas.py       # CLI fino (argparse + orquestração), importa de src/sucuri/
src/sucuri/
  api.py                   # Cliente da API do Portal da Transparência
  features.py               # Engenharia de variáveis e construção dos painéis A/B
  persistencia.py           # Salvamento de CSV/Parquet/JSON bruto e dicionário
  utils.py                  # brl_para_float, razao_segura, classificar_instituicao
tests/                     # Testes unitários (pytest) das funções de src/sucuri/
analises/                  # Scripts de análise por fase do ROADMAP (analises/NN_nome.py)
dados/
  despesas_ensino_superior.{csv,parquet}   # Conjunto A: funcional-programático
  despesas_por_instituicao.{csv,parquet}   # Conjunto B: por órgão do MEC
  DICIONARIO.md                            # Dicionário de dados (gerado pelo coletor)
  raw/*.json                               # Respostas brutas da API (com carimbo de data)
  externos/                                # Dados baixados manualmente (ver EXTERNAL.md)
relatorios/
  RELATORIO.md              # Relatório consolidado em Markdown — ver seção abaixo
  latex/relatorios.tex       # Mesmo relatório em LaTeX + relatorios.pdf compilado
  figuras/                   # Figuras geradas pelos scripts de analises/
ROADMAP.md                 # Plano de trabalho em fases/tarefas (siga-o)
EXTERNAL.md                 # Ações externas: chave de API, downloads manuais, comandos
```

## Os dois conjuntos de dados (leia antes de analisar)
- **Conjunto A** (`despesas_ensino_superior`): endpoint
  `/despesas/por-funcional-programatica`, função 12 (Educação) + subfunção 364
  (Ensino Superior). Granularidade: ano × programa × ação, nível federal.
  ~1.3k linhas, 2014–2026, 239 séries (`chave_serie` = programa-ação).
  **Atenção: distribuição muito esparsa — a mediana de empenhado/liquidado/pago
  é zero.** Muitas séries são curtas ou intermitentes; z-scores por série são
  pouco confiáveis nesses casos.
- **Conjunto B** (`despesas_por_instituicao`): endpoint `/despesas/por-orgao`,
  órgão superior 26000 (MEC). Cada linha é o **TOTAL do órgão no ano (todas as
  funções)**, não apenas ensino superior. ~1.5k linhas, ~115 órgãos
  (universidades, IFs, EBSERH, CAPES, FNDE etc.), com `tipo_instituicao`
  derivada para comparação entre pares.

## Ressalvas conhecidas (não redescubra)
- **2026 é ano parcial** (coleta de jul/2026): quedas em 2026 NÃO são anomalias.
  Excluir ou tratar o ano corrente em qualquer análise de série temporal.
- Valores são **nominais** (R$ correntes). Deflacionar por IPCA antes de
  comparar entre anos (ver ROADMAP fase 1).
- As colunas `flag_*` dos datasets são regras simples geradas na coleta —
  tratá-las como rótulos fracos/ponto de partida, não como verdade.
- O Conjunto B não permite concluir "gasto com ensino superior da instituição";
  para subfunção 364 use o Conjunto A.

## Ambiente e convenções
- O `python3` do sistema NÃO tem pandas. O projeto é gerenciado por `uv`
  (instalado em `~/.local/bin/uv`) via `pyproject.toml`: rode
  `uv sync --group dev` uma vez e depois `uv run python ...`,
  `uv run pytest`, `uv run ruff check .` normalmente.
- Lógica reutilizável fica em `src/sucuri/` (pacote `sucuri`); scripts de CLI
  e de análise apenas importam dele — não duplicar fórmulas/regras.
- Toda função nova em `src/sucuri/` que tenha lógica não trivial (conversões,
  fórmulas, regras de flag) deve ganhar teste em `tests/` (ver `tests/test_utils.py`
  e `tests/test_features.py` como referência de estilo e casos de borda:
  divisão por zero, série com desvio-padrão zero, valores nulos).
- Chave da API: variável `GOVBR_API_KEY` em `/Users/leseixas/.env`
  (**nunca** commitar nem imprimir). Detalhes em EXTERNAL.md.
- Limite da API: ~90 req/min (6h–24h); o coletor já faz pausa de 0,8s + backoff.
- Código, nomes de colunas, comentários e documentação em **português**,
  seguindo o estilo de `coletar_despesas.py` (snake_case, sem acentos em
  identificadores).
- Dados tratados: salvar sempre CSV + Parquet em `dados/`; brutos em
  `dados/raw/` com carimbo `_YYYYMMDD`.
- Recoletar dados: `uv run python coletar_despesas.py`
  (opções: `--ano-inicio`, `--ano-fim`, `--somente funcional|instituicao`).

## Registro de análises e relatórios

**Toda tarefa do ROADMAP que produza uma análise, uma medida estatística, um
modelo ou uma interpretação de dados reais (a partir da Fase 1 em diante)
deve ser registrada em DOIS lugares, sempre em conjunto com o código/dados
gerados — nunca apenas como código ou apenas como arquivo de saída:**

1. **`relatorios/RELATORIO.md`** — nova seção em Markdown descrevendo: o que
   foi medido, o método usado, o resultado numérico (tabelas/valores) e a
   interpretação (o que isso significa para a detecção de anomalias, com a
   ressalva de que atipicidade estatística ≠ irregularidade).
2. **`relatorios/latex/relatorios.tex`** — a mesma seção reescrita em LaTeX
   (mesmo conteúdo, formatação apropriada com `table`/`tabular`, `itemize`
   etc.), seguida de recompilação do PDF:
   ```bash
   cd relatorios/latex
   /Library/TeX/texbin/pdflatex -interaction=nonstopmode -halt-on-error relatorios.tex
   /Library/TeX/texbin/pdflatex -interaction=nonstopmode -halt-on-error relatorios.tex  # 2ª passagem: sumário/refs
   rm -f relatorios.aux relatorios.log relatorios.out relatorios.toc
   ```
   (mantenha apenas `relatorios.tex` e `relatorios.pdf` versionados nessa
   pasta; arquivos auxiliares do LaTeX não devem ser commitados).

Regras de conteúdo para ambas as versões:
- Nunca reportar um número sem dizer o método/fórmula usado para chegar nele.
- Sempre marcar explicitamente resultados afetados pelo ano parcial ou por
  séries curtas (ver "Ressalvas conhecidas" acima) — não deixe implícito.
- Usar linguagem de indício/atipicidade, nunca de acusação ou confirmação de
  irregularidade.
- Ao final de cada tarefa, adicionar a seção nova ao final do relatório
  existente (não reescrever o histórico de fases já documentadas), e marcar a
  tarefa correspondente como concluída em `ROADMAP.md`.

## Fluxo de trabalho
1. Consulte o ROADMAP.md e execute as tarefas na ordem das fases (cada tarefa
   tem entradas, saídas e critérios de aceite).
2. Ao concluir uma tarefa, marque-a no ROADMAP.md (`[x]`) e registre desvios.
3. Ações que dependem do usuário (downloads manuais, cadastro de chaves,
   comandos longos de coleta) estão em EXTERNAL.md — não tente executá-las
   automaticamente; sinalize quando forem pré-requisito.
