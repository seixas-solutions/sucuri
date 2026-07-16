"""Testes de sucuri.features: indicadores de execução e detecção de anomalias."""

import math

import pandas as pd
import pytest

from sucuri.features import (
    consolidar_flags,
    deduplicar_series,
    features_serie_temporal,
    indicadores_execucao,
    marcar_ano_parcial,
    marcar_series_curtas,
    recalcular_serie_temporal_confiavel,
    recalcular_zscore_entre_pares_confiavel,
    zscore_entre_pares,
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

    def test_coluna_valor_alternativa_usa_valores_dessa_coluna(self):
        """`coluna_valor` (tarefa 1.2/1.3) permite calcular sobre `pago_real`
        em vez de `pago`, mantendo os mesmos nomes de coluna de saída."""
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1"],
            "ano": [2020, 2021],
            "pago": [100.0, 100.0],       # nominal: sem variação
            "pago_real": [100.0, 300.0],  # real: salto de 200%
        })
        df = features_serie_temporal(df, chave="chave_serie", coluna_valor="pago_real")
        assert df["variacao_pago_aa"].iloc[1] == pytest.approx(2.0)
        assert bool(df["flag_salto_anual"].iloc[1]) is True


class TestZscoreEntrePares:
    def test_instituicao_atipica_e_sinalizada(self):
        # z-score clássico é sensível ao tamanho da amostra: um outlier
        # extremo também infla o desvio-padrão do grupo, então o exemplo
        # precisa de várias instituições "normais" e um outlier bem afastado
        # para o z-score do outlier realmente ultrapassar o limiar de 3.
        df = pd.DataFrame({
            "ano": [2024] * 20,
            "tipo_instituicao": ["Universidade Federal"] * 20,
            "pago": [100.0] * 19 + [100000.0],
        })
        df = zscore_entre_pares(df)
        assert bool(df["flag_atipico_entre_pares"].iloc[-1]) is True
        assert bool(df["flag_atipico_entre_pares"].iloc[0]) is False

    def test_grupos_diferentes_nao_se_misturam(self):
        df = pd.DataFrame({
            "ano": [2024, 2024],
            "tipo_instituicao": ["Universidade Federal", "CAPES"],
            "pago": [100.0, 100.0],
        })
        df = zscore_entre_pares(df)
        assert math.isnan(df["zscore_pago_entre_pares"].iloc[0])
        assert math.isnan(df["zscore_pago_entre_pares"].iloc[1])

    def test_coluna_valor_parametrizavel(self):
        df = pd.DataFrame({
            "ano": [2024, 2024],
            "tipo_instituicao": ["Universidade Federal", "Universidade Federal"],
            "pago": [1.0, 1.0],
            "pago_real": [100.0, 300.0],
        })
        df = zscore_entre_pares(df, coluna_valor="pago_real")
        assert df["zscore_pago_entre_pares"].iloc[0] < 0
        assert df["zscore_pago_entre_pares"].iloc[1] > 0


class TestMarcarSeriesCurtas:
    def test_serie_com_poucos_anos_e_marcada(self):
        df = pd.DataFrame({
            "chave_serie": ["curta", "curta", "longa", "longa", "longa", "longa", "longa"],
            "ano": [2020, 2021, 2018, 2019, 2020, 2021, 2022],
        })
        df = marcar_series_curtas(df, chave="chave_serie", min_anos=5)
        assert df.loc[df["chave_serie"] == "curta", "serie_curta"].all()
        assert not df.loc[df["chave_serie"] == "longa", "serie_curta"].any()


class TestMarcarAnoParcial:
    def test_apenas_ano_da_coleta_e_marcado(self):
        df = pd.DataFrame({"ano": [2024, 2025, 2026]})
        df = marcar_ano_parcial(df, ano_parcial=2026)
        assert df["ano_parcial"].tolist() == [False, False, True]


class TestDeduplicarSeries:
    def test_sem_duplicatas_retorna_inalterado(self):
        df = pd.DataFrame({"ano": [2020, 2021], "chave_serie": ["s1", "s1"], "pago": [10.0, 20.0]})
        resultado = deduplicar_series(df, chave=["ano", "chave_serie"], colunas_soma=["pago"])
        assert len(resultado) == 2

    def test_duplicatas_sao_somadas(self):
        df = pd.DataFrame({
            "ano": [2020, 2020],
            "chave_serie": ["s1", "s1"],
            "programa": ["NOME CURTO", "NOME COMPLETO ACENTUADO"],
            "pago": [0.0, 500.0],
        })
        resultado = deduplicar_series(df, chave=["ano", "chave_serie"], colunas_soma=["pago"])
        assert len(resultado) == 1
        assert resultado["pago"].iloc[0] == 500.0

    def test_prefere_rotulo_textual_mais_longo(self):
        df = pd.DataFrame({
            "ano": [2020, 2020],
            "chave_serie": ["s1", "s1"],
            "programa": ["BOLSAPERMANENCIA", "BOLSA PERMANENCIA COMPLETA"],
            "pago": [0.0, 0.0],
        })
        resultado = deduplicar_series(df, chave=["ano", "chave_serie"], colunas_soma=["pago"])
        assert resultado["programa"].iloc[0] == "BOLSA PERMANENCIA COMPLETA"


class TestRecalcularSerieTemporalConfiavel:
    def test_serie_curta_fica_com_nan_e_flags_false(self):
        df = pd.DataFrame({
            "chave_serie": ["s1", "s1"],
            "ano": [2020, 2021],
            "pago_real": [100.0, 1000.0],
            "serie_curta": [True, True],
            "ano_parcial": [False, False],
        })
        resultado = recalcular_serie_temporal_confiavel(df, chave="chave_serie")
        assert resultado["zscore_pago"].isna().all()
        assert not resultado["flag_salto_anual"].any()

    def test_ano_parcial_excluido_da_base_mas_outros_anos_calculados(self):
        df = pd.DataFrame({
            "chave_serie": ["s1"] * 6,
            "ano": [2019, 2020, 2021, 2022, 2023, 2026],
            "pago_real": [100.0, 100.0, 100.0, 100.0, 100.0, 5.0],
            "serie_curta": [False] * 6,
            "ano_parcial": [False, False, False, False, False, True],
        })
        resultado = recalcular_serie_temporal_confiavel(df, chave="chave_serie")
        linha_parcial = resultado[resultado["ano"] == 2026].iloc[0]
        assert math.isnan(linha_parcial["zscore_pago"])
        assert bool(linha_parcial["flag_salto_anual"]) is False
        # anos completos (constantes) não devem ser sinalizados como anômalos
        # por causa do valor baixo do ano parcial excluído.
        linha_2023 = resultado[resultado["ano"] == 2023].iloc[0]
        assert bool(linha_2023["flag_anomalia_zscore"]) is False


class TestRecalcularZscoreEntreParesConfiavel:
    def test_ano_parcial_recebe_nan_e_false(self):
        df = pd.DataFrame({
            "chave_serie": ["s1", "s2"],
            "ano": [2026, 2026],
            "tipo_instituicao": ["Universidade Federal", "Universidade Federal"],
            "pago_real": [10.0, 10000.0],
            "ano_parcial": [True, True],
        })
        resultado = recalcular_zscore_entre_pares_confiavel(df)
        assert resultado["zscore_pago_entre_pares"].isna().all()
        assert not resultado["flag_atipico_entre_pares"].any()

    def test_ano_completo_e_avaliado_normalmente(self):
        n = 20
        df = pd.DataFrame({
            "chave_serie": [f"s{i}" for i in range(n)],
            "ano": [2025] * n,
            "tipo_instituicao": ["Universidade Federal"] * n,
            "pago_real": [100.0] * (n - 1) + [100000.0],
            "ano_parcial": [False] * n,
        })
        resultado = recalcular_zscore_entre_pares_confiavel(df)
        assert bool(resultado.loc[resultado["chave_serie"] == f"s{n - 1}", "flag_atipico_entre_pares"].iloc[0]) is True


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
