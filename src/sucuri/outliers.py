"""Detecção de outliers multivariados: Isolation Forest e Local Outlier Factor.

Ambos os métodos recebem as mesmas features padronizadas (média 0, desvio
1) e produzem um score onde **maior = mais anômalo** (convenção unificada;
os dois algoritmos, na implementação do scikit-learn, produzem o oposto
nativamente). Um score combinado consolida os dois métodos via média dos
ranks normalizados — não depende de os scores brutos serem comparáveis
entre si (não são: escalas diferentes).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

AMOSTRA_MINIMA = 20


def preparar_features(df: pd.DataFrame, colunas: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    """Descarta linhas com algum NaN nas `colunas` e padroniza (z-score).

    Linhas com `ano_parcial=True` ou `serie_curta=True` já têm
    `variacao_pago_aa`/`zscore_*` como NaN (tarefa 1.3) e são
    naturalmente excluídas se essas colunas estiverem entre `colunas`.
    """
    completos = df.dropna(subset=colunas).copy()
    if completos.empty:
        return completos, np.empty((0, len(colunas)))
    X = StandardScaler().fit_transform(completos[colunas])
    return completos, X


def detectar_isolation_forest(X: np.ndarray, random_state: int = 42) -> np.ndarray:
    """Score de anomalia via Isolation Forest — maior = mais anômalo."""
    modelo = IsolationForest(random_state=random_state, n_estimators=200)
    modelo.fit(X)
    return -modelo.score_samples(X)


def detectar_lof(X: np.ndarray, n_vizinhos: int = 20) -> np.ndarray:
    """Score de anomalia via Local Outlier Factor — maior = mais anômalo."""
    n_vizinhos_efetivo = max(1, min(n_vizinhos, len(X) - 1))
    modelo = LocalOutlierFactor(n_neighbors=n_vizinhos_efetivo)
    modelo.fit_predict(X)
    return -modelo.negative_outlier_factor_


def _rank_normalizado(serie: pd.Series) -> pd.Series:
    """Rank normalizado em [0, 1], 1 = mais anômalo (maior score)."""
    n = len(serie)
    if n <= 1:
        return pd.Series(1.0, index=serie.index)
    rank = serie.rank(ascending=False, method="min")
    return 1 - (rank - 1) / (n - 1)


def aplicar_deteccao(
    df: pd.DataFrame,
    colunas_features: list[str],
    min_amostras: int = AMOSTRA_MINIMA,
    n_vizinhos: int = 20,
) -> pd.DataFrame | None:
    """Roda Isolation Forest + LOF sobre `df[colunas_features]`.

    Retorna `None` se a amostra elegível (sem NaN nas features) for menor
    que `min_amostras` — resultado inconclusivo, não deve ser calculado
    (LOF em particular não é significativo com poucas amostras: o número
    de vizinhos usado já é limitado a `len(X) - 1`).
    Caso contrário, retorna cópia de `df` restrita às linhas elegíveis com
    as colunas `score_isolation_forest`, `score_lof`, `rank_isolation_forest`,
    `rank_lof`, `score_anomalia` (média dos ranks normalizados dos dois
    métodos) e `rank_anomalia` adicionadas.
    """
    completos, X = preparar_features(df, colunas_features)
    if len(completos) < min_amostras:
        return None

    completos["score_isolation_forest"] = detectar_isolation_forest(X)
    completos["score_lof"] = detectar_lof(X, n_vizinhos=n_vizinhos)
    completos["rank_isolation_forest"] = (
        completos["score_isolation_forest"].rank(ascending=False, method="min").astype(int)
    )
    completos["rank_lof"] = completos["score_lof"].rank(ascending=False, method="min").astype(int)

    # Scores normalizados (0-1, dentro do grupo recebido) por método — usados
    # tanto no score combinado quanto para comparar/ordenar entre grupos de
    # tamanhos diferentes quando `df` é processado por partes (ex.: Conjunto
    # B, um modelo por tipo_instituicao) e depois concatenado pelo chamador.
    # Ranks/scores brutos (`rank_isolation_forest`, `score_lof` etc.) são
    # sempre relativos ao grupo recebido nesta chamada, nunca globais.
    completos["score_norm_isolation_forest"] = _rank_normalizado(completos["score_isolation_forest"])
    completos["score_norm_lof"] = _rank_normalizado(completos["score_lof"])
    completos["score_anomalia"] = (completos["score_norm_isolation_forest"] + completos["score_norm_lof"]) / 2
    completos["rank_anomalia"] = completos["score_anomalia"].rank(ascending=False, method="min").astype(int)
    return completos


def recalcular_ranks_globais(df: pd.DataFrame) -> pd.DataFrame:
    """Recalcula `rank_isolation_forest`, `rank_lof` e `rank_anomalia` como
    ranks GLOBAIS sobre `df` inteiro, a partir dos scores normalizados
    (0-1) por método. Necessário depois de concatenar resultados de
    `aplicar_deteccao` rodados em grupos separados (ex.: um por
    `tipo_instituicao`) — sem isso, o rank de cada linha só é válido dentro
    do seu próprio grupo (várias linhas empatadas em rank=1, uma por
    grupo), o que quebra qualquer seleção de "top N" ou comparação entre
    métodos feita sobre o conjunto concatenado.
    """
    df = df.copy()
    df["rank_isolation_forest"] = df["score_norm_isolation_forest"].rank(ascending=False, method="min").astype(int)
    df["rank_lof"] = df["score_norm_lof"].rank(ascending=False, method="min").astype(int)
    df["rank_anomalia"] = df["score_anomalia"].rank(ascending=False, method="min").astype(int)
    return df


def concordancia_top_n(
    df: pd.DataFrame, coluna_a: str, coluna_b: str, top_pct: float = 0.10
) -> dict:
    """Sobreposição (índice de Jaccard) entre o top `top_pct` de duas colunas
    de rank (menor rank = mais anômalo)."""
    n = len(df)
    k = max(1, int(round(n * top_pct)))
    top_a = set(df.nsmallest(k, coluna_a).index)
    top_b = set(df.nsmallest(k, coluna_b).index)
    intersecao = top_a & top_b
    uniao = top_a | top_b
    return {
        "n": n,
        "k": k,
        "intersecao": len(intersecao),
        "jaccard": len(intersecao) / len(uniao) if uniao else float("nan"),
    }
