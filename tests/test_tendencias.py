"""Testes de sucuri.tendencias: Theil–Sen e detecção de eventos por série."""

import numpy as np
import pandas as pd
import pytest

from sucuri.tendencias import ajustar_theil_sen, detectar_eventos_serie, residuos_robustos


class TestAjustarTheilSen:
    def test_reta_perfeita_recupera_inclinacao_exata(self):
        anos = np.array([2018, 2019, 2020, 2021, 2022])
        valores = 100.0 + 10.0 * (anos - 2018)
        inclinacao, intercepto = ajustar_theil_sen(anos, valores)
        assert inclinacao == pytest.approx(10.0)
        # intercepto é o valor previsto em x=0 (ano=0), não em anos[0] —
        # comparar o valor previsto no primeiro ano observado, não o
        # intercepto bruto.
        valor_previsto_no_primeiro_ano = intercepto + inclinacao * anos[0]
        assert valor_previsto_no_primeiro_ano == pytest.approx(100.0)

    def test_pouco_sensivel_a_um_outlier(self):
        anos = np.array([2015, 2016, 2017, 2018, 2019, 2020, 2021])
        valores = 100.0 + 10.0 * (anos - 2015)
        valores_com_outlier = valores.copy()
        valores_com_outlier[3] += 10000  # um ponto muito fora da reta
        inclinacao_limpa, _ = ajustar_theil_sen(anos, valores)
        inclinacao_com_outlier, _ = ajustar_theil_sen(anos, valores_com_outlier)
        # a inclinação não deve se mover muito por causa de um único ponto
        assert abs(inclinacao_com_outlier - inclinacao_limpa) < 5.0


class TestResiduosRobustos:
    def test_serie_sem_ruido_desvio_zero(self):
        anos = np.array([2018, 2019, 2020, 2021])
        valores = 100.0 + 5.0 * (anos - 2018)
        residuos, desvio = residuos_robustos(anos, valores)
        assert desvio == pytest.approx(0.0, abs=1e-9)
        assert np.allclose(residuos, 0.0, atol=1e-9)

    def test_ponto_fora_da_tendencia_tem_residuo_grande(self):
        anos = np.array([2018, 2019, 2020, 2021, 2022])
        valores = np.array([100.0, 110.0, 500.0, 130.0, 140.0])
        residuos, _ = residuos_robustos(anos, valores)
        assert abs(residuos[2]) > abs(residuos[0])
        assert abs(residuos[2]) > abs(residuos[4])


class TestDetectarEventosSerie:
    def _df_serie(self, chave_valor, anos, valores):
        return pd.DataFrame({"chave_serie": chave_valor, "ano": anos, "pago_real": valores})

    def test_serie_curta_e_ignorada(self):
        df = self._df_serie("org1", [2020, 2021, 2022], [100.0, 200.0, 5000.0])
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8)
        assert eventos.empty

    def test_evento_detectado_em_serie_longa(self):
        anos = list(range(2014, 2026))  # 12 anos
        valores = [100.0 + 10 * (a - 2014) for a in anos]
        valores[6] = 5000.0  # ponto muito fora da tendência
        df = self._df_serie("org1", anos, valores)
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8, limiar_desvio=2.5)
        assert len(eventos) >= 1
        assert eventos.iloc[0]["ano"] == anos[6]

    def test_serie_sem_desvio_nao_gera_falso_positivo(self):
        anos = list(range(2014, 2026))
        valores = [100.0 + 10 * (a - 2014) for a in anos]  # tendência perfeita
        df = self._df_serie("org1", anos, valores)
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8)
        assert eventos.empty

    def test_multiplas_series_processadas_independentemente(self):
        anos = list(range(2014, 2026))
        valores_normais = [100.0 + 10 * (a - 2014) for a in anos]
        valores_com_evento = valores_normais.copy()
        valores_com_evento[3] = 9000.0
        df = pd.concat([
            self._df_serie("normal", anos, valores_normais),
            self._df_serie("com_evento", anos, valores_com_evento),
        ], ignore_index=True)
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8)
        assert set(eventos["chave_serie"]) == {"com_evento"}

    def test_resultado_ordenado_por_desvio_absoluto_decrescente(self):
        anos = list(range(2014, 2026))
        valores = [100.0 + 10 * (a - 2014) for a in anos]
        valores[2] = 3000.0
        valores[8] = 2000.0
        df = self._df_serie("org1", anos, valores)
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8)
        desvios = eventos["desvio_padronizado"].abs().tolist()
        assert desvios == sorted(desvios, reverse=True)

    def test_sem_eventos_retorna_dataframe_vazio_com_colunas(self):
        anos = list(range(2014, 2026))
        valores = [100.0 + 10 * (a - 2014) for a in anos]
        df = self._df_serie("org1", anos, valores)
        eventos = detectar_eventos_serie(df, chave="chave_serie", min_anos=8)
        assert list(eventos.columns) == [
            "chave_serie", "ano", "pago_real", "residuo", "desvio_padronizado", "n_anos_serie"
        ]
