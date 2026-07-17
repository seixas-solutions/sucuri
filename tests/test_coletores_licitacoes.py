"""Testes de sucuri.coletores.licitacoes — sem chamadas de rede reais."""

from datetime import date
from unittest.mock import patch

import pandas as pd

from sucuri.coletores.licitacoes import (
    construir_df_licitacoes,
    desertas_repetidas,
    _meses_no_intervalo,
    coletar_licitacoes_periodo,
)


def _licitacao_fake(codigo_orgao="26236", situacao="Homologada", numero_processo="123"):
    return {
        "id": 1,
        "licitacao": {"numero": "1/2024", "numeroProcesso": numero_processo, "objeto": "objeto teste"},
        "situacaoCompra": situacao,
        "modalidadeLicitacao": "Pregão",
        "dataAbertura": "2024-03-10",
        "dataResultadoCompra": "2024-03-20",
        "valor": 1000.0,
        "unidadeGestora": {"orgaoVinculado": {"codigoSIAFI": codigo_orgao, "nome": "Órgão Teste"}},
    }


class TestMesesNoIntervalo:
    def test_mesmo_mes(self):
        assert _meses_no_intervalo(date(2024, 3, 1), date(2024, 3, 31)) == [(2024, 3)]

    def test_atravessa_ano(self):
        assert _meses_no_intervalo(date(2023, 11, 1), date(2024, 2, 1)) == [
            (2023, 11), (2023, 12), (2024, 1), (2024, 2),
        ]


class TestColetarLicitacoesPeriodo:
    def test_uma_requisicao_por_mes(self):
        with patch("sucuri.coletores.licitacoes.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_licitacoes_periodo(
                sessao="s", codigo_orgao="26236",
                data_inicio=date(2024, 1, 1), data_fim=date(2024, 3, 31),
            )
        assert mock_coletar.call_count == 3

    def test_datas_do_mes_completo(self):
        with patch("sucuri.coletores.licitacoes.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_licitacoes_periodo(
                sessao="s", codigo_orgao="26236",
                data_inicio=date(2024, 2, 1), data_fim=date(2024, 2, 28),
            )
        args, _ = mock_coletar.call_args
        _sessao, _endpoint, params, _rotulo = args
        assert params["dataInicial"] == "01/02/2024"
        assert params["dataFinal"] == "29/02/2024"  # 2024 é bissexto


class TestConstruirDfLicitacoes:
    def test_lista_vazia(self):
        assert construir_df_licitacoes([]).empty

    def test_extrai_campos(self):
        df = construir_df_licitacoes([_licitacao_fake()])
        assert df["codigoOrgao"].iloc[0] == "26236"
        assert df["numeroProcesso"].iloc[0] == "123"
        assert df["ano"].iloc[0] == 2024

    def test_detecta_deserta(self):
        df = construir_df_licitacoes([_licitacao_fake(situacao="Licitação Deserta")])
        assert bool(df["eh_deserta_ou_fracassada"].iloc[0]) is True

    def test_detecta_fracassada(self):
        df = construir_df_licitacoes([_licitacao_fake(situacao="Fracassada por ausência de propostas")])
        assert bool(df["eh_deserta_ou_fracassada"].iloc[0]) is True

    def test_homologada_nao_e_deserta(self):
        df = construir_df_licitacoes([_licitacao_fake(situacao="Homologada")])
        assert bool(df["eh_deserta_ou_fracassada"].iloc[0]) is False


class TestDesertasRepetidas:
    def test_abaixo_do_minimo_nao_aparece(self):
        df = construir_df_licitacoes([_licitacao_fake(situacao="Deserta")])
        resultado = desertas_repetidas(df, min_ocorrencias=2)
        assert resultado.empty

    def test_repetidas_aparecem(self):
        registros = [_licitacao_fake(situacao="Deserta") for _ in range(3)]
        df = construir_df_licitacoes(registros)
        resultado = desertas_repetidas(df, min_ocorrencias=2)
        assert len(resultado) == 1
        assert resultado["n_desertas_fracassadas"].iloc[0] == 3

    def test_df_vazio_nao_gera_erro(self):
        resultado = desertas_repetidas(pd.DataFrame())
        assert resultado.empty
