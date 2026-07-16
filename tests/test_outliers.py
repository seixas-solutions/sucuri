"""Testes de sucuri.outliers: preparação de features e detecção de outliers."""

import numpy as np
import pandas as pd
import pytest

from sucuri.outliers import (
    aplicar_deteccao,
    concordancia_top_n,
    detectar_isolation_forest,
    detectar_lof,
    preparar_features,
    recalcular_ranks_globais,
)


def _df_com_outlier(n_normais: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    normais = pd.DataFrame({
        "x": rng.normal(0, 1, n_normais),
        "y": rng.normal(0, 1, n_normais),
    })
    outlier = pd.DataFrame({"x": [50.0], "y": [50.0]})
    return pd.concat([normais, outlier], ignore_index=True)


class TestPrepararFeatures:
    def test_descarta_linhas_com_nan(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [1.0, 2.0, 3.0]})
        completos, x = preparar_features(df, ["a", "b"])
        assert len(completos) == 2
        assert x.shape == (2, 2)

    def test_padroniza_media_zero(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0]})
        _, x = preparar_features(df, ["a"])
        assert x.mean() == pytest.approx(0.0, abs=1e-9)

    def test_todas_linhas_com_nan_retorna_vazio(self):
        df = pd.DataFrame({"a": [np.nan, np.nan]})
        completos, x = preparar_features(df, ["a"])
        assert completos.empty
        assert x.shape == (0, 1)


class TestDetectarIsolationForest:
    def test_outlier_recebe_score_maior(self):
        df = _df_com_outlier()
        _, x = preparar_features(df, ["x", "y"])
        scores = detectar_isolation_forest(x)
        assert scores[-1] == scores.max()


class TestDetectarLof:
    def test_outlier_recebe_score_maior(self):
        df = _df_com_outlier()
        _, x = preparar_features(df, ["x", "y"])
        scores = detectar_lof(x, n_vizinhos=20)
        assert scores[-1] == scores.max()

    def test_n_vizinhos_maior_que_amostra_nao_gera_erro(self):
        df = _df_com_outlier(n_normais=5)
        _, x = preparar_features(df, ["x", "y"])
        scores = detectar_lof(x, n_vizinhos=1000)
        assert len(scores) == len(x)


class TestAplicarDeteccao:
    def test_amostra_pequena_retorna_none(self):
        df = _df_com_outlier(n_normais=5)
        resultado = aplicar_deteccao(df, ["x", "y"], min_amostras=20)
        assert resultado is None

    def test_amostra_suficiente_retorna_colunas_esperadas(self):
        df = _df_com_outlier(n_normais=40)
        resultado = aplicar_deteccao(df, ["x", "y"], min_amostras=20)
        assert resultado is not None
        for col in ("score_isolation_forest", "score_lof", "rank_isolation_forest",
                    "rank_lof", "score_anomalia", "rank_anomalia"):
            assert col in resultado.columns

    def test_outlier_conhecido_fica_no_topo_do_rank_anomalia(self):
        df = _df_com_outlier(n_normais=40)
        resultado = aplicar_deteccao(df, ["x", "y"], min_amostras=20)
        linha_outlier = resultado[(resultado["x"] > 10)]
        assert linha_outlier["rank_anomalia"].iloc[0] == 1

    def test_score_anomalia_entre_zero_e_um(self):
        df = _df_com_outlier(n_normais=40)
        resultado = aplicar_deteccao(df, ["x", "y"], min_amostras=20)
        assert resultado["score_anomalia"].between(0, 1).all()


class TestRecalcularRanksGlobais:
    def test_rank_passa_a_cobrir_toda_a_faixa_concatenada(self):
        """Simula o caso real (Conjunto B): dois grupos processados
        separadamente por `aplicar_deteccao` têm rank local 1..n cada um
        (o ponto mais extremo de cada grupo normaliza para score 1.0 — um
        empate no topo entre os dois grupos é legítimo, já que o score é
        relativo aos pares de cada grupo). O que o rank global deve
        corrigir é o rank MÁXIMO ficar preso ao tamanho de um grupo em vez
        de refletir o total concatenado."""
        grupo1 = aplicar_deteccao(_df_com_outlier(n_normais=25, seed=1), ["x", "y"], min_amostras=20)
        grupo2 = aplicar_deteccao(_df_com_outlier(n_normais=25, seed=2), ["x", "y"], min_amostras=20)
        concatenado = pd.concat([grupo1, grupo2], ignore_index=True)
        # Antes de recalcular: rank local, preso ao tamanho de cada grupo.
        assert concatenado["rank_anomalia"].max() < len(concatenado)

        recalculado = recalcular_ranks_globais(concatenado)
        assert recalculado["rank_anomalia"].max() == len(recalculado)
        assert recalculado["rank_anomalia"].min() == 1

    def test_grupo_unico_e_idempotente(self):
        df = _df_com_outlier(n_normais=40)
        resultado = aplicar_deteccao(df, ["x", "y"], min_amostras=20)
        recalculado = recalcular_ranks_globais(resultado)
        assert (resultado["rank_anomalia"] == recalculado["rank_anomalia"]).all()


class TestConcordanciaTopN:
    def test_ranks_identicos_jaccard_um(self):
        df = pd.DataFrame({"rank_a": [1, 2, 3, 4, 5], "rank_b": [1, 2, 3, 4, 5]})
        resultado = concordancia_top_n(df, "rank_a", "rank_b", top_pct=0.4)
        assert resultado["jaccard"] == pytest.approx(1.0)

    def test_ranks_opostos_jaccard_baixo(self):
        df = pd.DataFrame({"rank_a": [1, 2, 3, 4, 5], "rank_b": [5, 4, 3, 2, 1]})
        resultado = concordancia_top_n(df, "rank_a", "rank_b", top_pct=0.2)
        assert resultado["jaccard"] == pytest.approx(0.0)
