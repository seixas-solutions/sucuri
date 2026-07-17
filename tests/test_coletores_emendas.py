"""Testes de sucuri.coletores.emendas — sem chamadas de rede reais."""

from unittest.mock import patch

import pandas as pd

from sucuri.coletores.emendas import (
    coletar_emendas_ano,
    coletar_emendas_intervalo,
    construir_df_emendas,
    marcar_ano_eleitoral,
)


def _emenda_fake(ano=2023, valor_pago="10.000,00", autor="FULANO"):
    return {
        "codigoEmenda": "1", "ano": ano, "tipoEmenda": "Emenda Individual",
        "autor": autor, "localidadeDoGasto": "SP (UF)",
        "funcao": "Educação", "subfuncao": "Ensino superior",
        "valorEmpenhado": valor_pago, "valorLiquidado": valor_pago, "valorPago": valor_pago,
    }


class TestColetarEmendasAno:
    def test_parametros_corretos(self):
        with patch("sucuri.coletores.emendas.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_emendas_ano(sessao="s", ano=2023)
        args, _ = mock_coletar.call_args
        _sessao, endpoint, params, _rotulo = args
        assert endpoint == "/emendas"
        assert params == {"ano": 2023, "codigoFuncao": "12", "codigoSubfuncao": "364"}


class TestColetarEmendasIntervalo:
    def test_uma_chamada_por_ano(self):
        with patch("sucuri.coletores.emendas.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_emendas_intervalo(sessao="s", ano_inicio=2020, ano_fim=2023)
        assert mock_coletar.call_count == 4


class TestConstruirDfEmendas:
    def test_lista_vazia(self):
        assert construir_df_emendas([]).empty

    def test_converte_valores(self):
        df = construir_df_emendas([_emenda_fake(valor_pago="1.234,56")])
        assert df["valorPago"].iloc[0] == 1234.56


class TestMarcarAnoEleitoral:
    def test_ano_eleitoral_geral_marcado(self):
        df = pd.DataFrame({"ano": [2022]})
        resultado = marcar_ano_eleitoral(df)
        assert bool(resultado["ano_eleitoral"].iloc[0]) is True

    def test_ano_eleitoral_municipal_marcado(self):
        df = pd.DataFrame({"ano": [2024]})
        resultado = marcar_ano_eleitoral(df)
        assert bool(resultado["ano_eleitoral"].iloc[0]) is True

    def test_ano_nao_eleitoral_nao_marcado(self):
        df = pd.DataFrame({"ano": [2023]})
        resultado = marcar_ano_eleitoral(df)
        assert bool(resultado["ano_eleitoral"].iloc[0]) is False
