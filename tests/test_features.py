"""Testes de sucuri.features: indicadores de execução e detecção de anomalias."""

import math

import pandas as pd
import pytest

from sucuri.features import (
    consolidar_flags,
    features_serie_temporal,
    indicadores_execucao,
)


def _df_execucao(empenhado, liquidado, pago):
    return pd.DataFrame({"empenhado": empenhado, "liquidado": liquidado, "pago": pago})


class TestIndicadoresExecucao:
    def test_taxas_e_saldos_caso_normal(self):
        df = _df_execucao([100.0], [80.0], [60.0])
        df = indicadores_execucao(df)
        assert df["taxa_liquidacao"].iloc[0] == 0.8
        assert df["taxa_pagamento"].iloc[0] == 0.6
        assert df["valor_a_liquidar"].iloc[0] == 20.0
        assert df["restos_a_pagar"].iloc[0] == 20.0

    def test_empenhado_zero_produz_taxas_nan_sem_erro(self):
        df = _df_execucao([0.0], [0.0], [0.0])
        df = indicadores_execucao(df)
        assert math.isnan(df["taxa_liquidacao"].iloc[0])
        assert math.isnan(df["taxa_pagamento"].iloc[0])

    def test_flag_pago_maior_empenhado(self):
        df = _df_execucao([100.0], [100.0], [150.0])
        df = indicadores_execucao(df)
        assert bool(df["flag_pago_maior_empenhado"].iloc[0]) is True

    def test_flag_liquidado_maior_empenhado(self):
        df = _df_execucao([100.0], [150.0], [100.0])
        df = indicadores_execucao(df)
        assert bool(df["flag_liquidado_maior_empenhado"].iloc[0]) is True

    def test_flag_valor_negativo(self):
        df = _df_execucao([-10.0], [0.0], [0.0])
        df = indicadores_execucao(df)
        assert bool(df["flag_valor_negativo"].iloc[0]) is True

    def test_sem_falso_positivo_em_valores_coerentes(self):
        df = _df_execucao([100.0], [80.0], [60.0])
        df = indicadores_execucao(df)
        assert bool(df["flag_pago_maior_empenhado"].iloc[0]) is False
        assert bool(df["flag_liquidado_maior_empenhado"].iloc[0]) is False
        assert bool(df["flag_valor_negativo"].iloc[0]) is False


class TestFeaturesSerieTemporal:
    def test_variacao_anual_calculada_corretamente(self):
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1", "s1"],
            "ano": [2020, 2021, 2022],
            "pago": [100.0, 150.0, 300.0],
        })
        df = features_serie_temporal(df, chave="chave_serie")
        assert math.isnan(df["variacao_pago_aa"].iloc[0])
        assert df["variacao_pago_aa"].iloc[1] == pytest.approx(0.5)
        assert df["variacao_pago_aa"].iloc[2] == pytest.approx(1.0)

    def test_flag_salto_anual_dispara_acima_de_100_por_cento(self):
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1"],
            "ano": [2020, 2021],
            "pago": [100.0, 300.0],
        })
        df = features_serie_temporal(df, chave="chave_serie")
        assert bool(df["flag_salto_anual"].iloc[1]) is True

    def test_serie_com_desvio_padrao_zero_nao_gera_erro(self):
        """Série constante: std=0 e MAD=0 não podem gerar ZeroDivisionError."""
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1", "s1"],
            "ano": [2020, 2021, 2022],
            "pago": [50.0, 50.0, 50.0],
        })
        df = features_serie_temporal(df, chave="chave_serie")
        assert df["zscore_pago"].isna().all()
        assert df["zscore_robusto_pago"].isna().all()
        assert not df["flag_anomalia_zscore"].any()
        assert not df["flag_anomalia_robusto"].any()

    def test_serie_unica_observacao(self):
        df = pd.DataFrame({"chave_serie": ["s1"], "ano": [2020], "pago": [100.0]})
        df = features_serie_temporal(df, chave="chave_serie")
        assert math.isnan(df["variacao_pago_aa"].iloc[0])
        assert math.isnan(df["zscore_pago"].iloc[0])

    def test_series_independentes_nao_se_misturam(self):
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1", "s2", "s2"],
            "ano": [2020, 2021, 2020, 2021],
            "pago": [100.0, 100.0, 1000.0, 5000.0],
        })
        df = features_serie_temporal(df, chave="chave_serie")
        var_s2 = df.loc[(df["chave_serie"] == "s2") & (df["ano"] == 2021), "variacao_pago_aa"].iloc[0]
        assert var_s2 == pytest.approx(4.0)


class TestConsolidarFlags:
    def test_nenhuma_flag_ativa(self):
        df = pd.DataFrame({
            "flag_anomalia_zscore": [False],
            "flag_anomalia_robusto": [False],
            "flag_salto_anual": [False],
            "flag_pago_maior_empenhado": [False],
            "flag_liquidado_maior_empenhado": [False],
            "flag_valor_negativo": [False],
        })
        df = consolidar_flags(df)
        assert bool(df["flag_anomalia"].iloc[0]) is False

    def test_uma_flag_ativa_consolida_true(self):
        df = pd.DataFrame({
            "flag_anomalia_zscore": [True],
            "flag_anomalia_robusto": [False],
            "flag_salto_anual": [False],
            "flag_pago_maior_empenhado": [False],
            "flag_liquidado_maior_empenhado": [False],
            "flag_valor_negativo": [False],
        })
        df = consolidar_flags(df)
        assert bool(df["flag_anomalia"].iloc[0]) is True

    def test_flag_extra_e_considerada(self):
        df = pd.DataFrame({
            "flag_anomalia_zscore": [False],
            "flag_anomalia_robusto": [False],
            "flag_salto_anual": [False],
            "flag_pago_maior_empenhado": [False],
            "flag_liquidado_maior_empenhado": [False],
            "flag_valor_negativo": [False],
            "flag_atipico_entre_pares": [True],
        })
        df = consolidar_flags(df, extra=["flag_atipico_entre_pares"])
        assert bool(df["flag_anomalia"].iloc[0]) is True

    def test_valores_nulos_tratados_como_false(self):
        df = pd.DataFrame({
            "flag_anomalia_zscore": [pd.NA],
            "flag_anomalia_robusto": [False],
            "flag_salto_anual": [False],
            "flag_pago_maior_empenhado": [False],
            "flag_liquidado_maior_empenhado": [False],
            "flag_valor_negativo": [False],
        })
        df = consolidar_flags(df)
        assert bool(df["flag_anomalia"].iloc[0]) is False
