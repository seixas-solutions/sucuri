# sucuri

Detecção de indícios de anomalias em despesas federais com Educação de
Nível Superior, a partir de dados públicos do [Portal da Transparência](https://portaldatransparencia.gov.br/)
(gov.br). O projeto coleta, trata e analisa a execução orçamentária do
Ministério da Educação (universidades federais, institutos federais/CEFETs,
hospitais universitários, CAPES, FNDE/FIES etc.), com o objetivo de sinalizar
padrões de gasto estatisticamente atípicos que mereçam checagem manual —
não de acusar irregularidade. **Atipicidade estatística não é prova de
irregularidade**; todo resultado deste projeto deve ser lido como indício a
investigar, nunca como conclusão.

## O que o projeto coleta

Dois conjuntos complementares, via API do Portal da Transparência:

- **Conjunto A** — despesas por função/subfunção (função 12 = Educação,
  subfunção 364 = Ensino Superior), nível federal, granularidade
  programa × ação.
- **Conjunto B** — despesas por órgão do Ministério da Educação (órgão
  superior 26000), uma linha por instituição/ano (total do órgão, todas as
  funções — não só ensino superior).

Ver `dados/DICIONARIO.md` para a descrição completa de colunas de cada
estágio do pipeline (dados originais, deflacionados, tratados).

## Estrutura do repositório

```
coletar_despesas.py       # CLI de coleta (API -> dados/)
src/sucuri/                # Pacote com a lógica reutilizável
  api.py                    # Cliente da API do Portal da Transparência
  features.py                # Engenharia de variáveis, flags de anomalia
  deflacao.py                 # Deflacionamento de valores pelo IPCA
  persistencia.py              # Salvamento de dados e dicionário de dados
  utils.py                      # Conversões e classificação de instituições
analises/                  # Scripts de análise, um por tarefa do ROADMAP
tests/                     # Testes unitários (pytest)
dados/                     # Dados coletados e tratados (ver dados/DICIONARIO.md)
relatorios/
  RELATORIO.md               # Relatório consolidado: métodos, resultados, interpretação
  latex/relatorios.tex         # Mesmo relatório em LaTeX, com PDF compilado
  01_qualidade.md, ...          # Relatórios específicos de cada tarefa
ROADMAP.md                 # Plano de trabalho em fases/tarefas
CLAUDE.md                  # Contexto do projeto para trabalho assistido por IA
EXTERNAL.md                # O que depende de ação humana: credenciais, downloads manuais
```

## Como rodar

Pré-requisito: [`uv`](https://docs.astral.sh/uv/) instalado.

```bash
uv sync --group dev          # cria o ambiente e instala as dependências

uv run pytest                # roda os testes
uv run ruff check .          # lint

# Pipeline de dados, em ordem:
uv run python coletar_despesas.py            # coleta bruta (requer GOVBR_API_KEY em ~/.env)
uv run python analises/00_baixar_ipca.py      # baixa o IPCA (Banco Central, API pública)
uv run python analises/01_qualidade.py         # relatório de qualidade dos dados
uv run python analises/01b_deflacionar.py       # deflaciona pelo IPCA -> dados/*_real.*
uv run python analises/01c_ano_parcial_e_flags.py  # trata ano parcial/duplicatas -> dados/*_v2.*
```

`dados/*_v2.{csv,parquet}` é o conjunto recomendado para qualquer análise de
anomalia — os estágios anteriores (dados originais e `*_real`) existem só
como etapas intermediárias do pipeline (ver `dados/DICIONARIO.md`).

## Estado atual

Fases 0 (infraestrutura) e 1 (qualidade dos dados, deflação, tratamento de
ano parcial) do `ROADMAP.md` concluídas. Detalhes de método, resultados e
interpretação de cada tarefa em `relatorios/RELATORIO.md` (ou
`relatorios/latex/relatorios.pdf`). Próximos passos e escopo completo
(detecção estatística de anomalias, cruzamento com contratos/licitações/
sanções do Portal da Transparência, validação contra fontes externas) em
`ROADMAP.md`.

## Ressalvas importantes

- O ano da coleta mais recente está sempre parcial (exercício orçamentário
  incompleto) — nunca comparar diretamente com anos completos sem o
  tratamento aplicado em `analises/01c_ano_parcial_e_flags.py`.
- Comparações de valores entre anos distantes devem usar as colunas
  deflacionadas (`*_real`), não os valores nominais.
- Este projeto não usa nem expõe a chave de API (`GOVBR_API_KEY`) em nenhum
  arquivo versionado — ver `EXTERNAL.md` para como configurá-la localmente.

## Licença

MIT — ver `LICENSE`.
