"""Deflacionamento de séries monetárias pelo IPCA (tarefa 1.2 do ROADMAP).

Converte valores nominais (R$ correntes) em valores reais (R$ do ano-base),
usando um índice de preços encadeado a partir do IPCA acumulado anual. O
ano-base recomendado é o último ano com os 12 meses de IPCA disponíveis
(`ano_completo=True` em `dados/externos/ipca_anual_detalhe.csv`), pois é
esse o ano corrente da coleta que costuma estar parcial (ver ressalva em
CLAUDE.md).

Fonte do IPCA: `dados/externos/ipca_anual.csv` (colunas `ano`,
`ipca_acumulado_pct`), obtido por `analises/00_baixar_ipca.py`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CAMINHO_IPCA_PADRAO = Path("dados/externos/ipca_anual.csv")


def carregar_ipca(caminho: Path | str = CAMINHO_IPCA_PADRAO) -> pd.DataFrame:
    """Carrega o IPCA anual acumulado. Levanta erro claro se o arquivo não existir.

    Corresponde ao pré-requisito E1 de EXTERNAL.md: sem este arquivo, a
    deflação não pode prosseguir.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo de IPCA não encontrado em '{caminho}'. Rode "
            "'uv run python analises/00_baixar_ipca.py' antes de deflacionar "
            "(ver EXTERNAL.md, item E1)."
        )
    return pd.read_csv(caminho)


def construir_indice_encadeado(ipca_df: pd.DataFrame) -> pd.Series:
    """Constrói um índice de preços encadeado a partir do IPCA acumulado anual.

    O índice não tem uma unidade absoluta significativa isoladamente — o que
    importa é a RAZÃO entre o índice de dois anos quaisquer, que reproduz a
    inflação acumulada entre eles. `indice[ano_b] / indice[ano_a]` é o fator
    de correção para levar um valor nominal do ano A ao poder de compra do
    ano B.
    """
    df = ipca_df.sort_values("ano").reset_index(drop=True)
    fator_anual = 1 + df["ipca_acumulado_pct"] / 100
    indice = fator_anual.cumprod()
    return pd.Series(indice.values, index=df["ano"].values, name="indice_ipca")


def deflacionar(
    df: pd.DataFrame,
    indice: pd.Series,
    ano_base: int,
    colunas: list[str],
    coluna_ano: str = "ano",
    sufixo: str = "_real",
) -> pd.DataFrame:
    """Adiciona colunas `<coluna><sufixo>` com os valores em R$ do `ano_base`.

    Linhas cujo ano não está no índice de IPCA recebem NaN nas colunas
    deflacionadas (em vez de erro), para não interromper o pipeline por um
    ano fora da cobertura do IPCA.
    """
    if ano_base not in indice.index:
        raise ValueError(f"Ano-base {ano_base} não está no índice de IPCA disponível.")

    df = df.copy()
    fator_por_ano = indice.loc[ano_base] / indice
    fator = df[coluna_ano].map(fator_por_ano)
    for col in colunas:
        df[f"{col}{sufixo}"] = df[col] * fator
    return df
