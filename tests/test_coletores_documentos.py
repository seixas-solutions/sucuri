"""Testes de sucuri.coletores.documentos — sem chamadas de rede reais (mock)."""

from datetime import date
from unittest.mock import patch

from sucuri.coletores.documentos import coletar_documentos_periodo


class TestColetarDocumentosPeriodo:
    def test_uma_requisicao_por_dia_por_fase(self):
        with patch("sucuri.coletores.documentos.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_documentos_periodo(
                sessao=object(), unidade_gestora="154046",
                data_inicio=date(2025, 5, 1), data_fim=date(2025, 5, 2),
                fases=(1, 2, 3),
            )
        # 2 dias x 3 fases = 6 chamadas.
        assert mock_coletar.call_count == 6

    def test_marca_fase_consultada_em_cada_registro(self):
        registros_falsos = [{"documento": "X1"}, {"documento": "X2"}]
        with patch("sucuri.coletores.documentos.coletar_paginado", return_value=registros_falsos):
            resultado = coletar_documentos_periodo(
                sessao=object(), unidade_gestora="154046",
                data_inicio=date(2025, 5, 1), data_fim=date(2025, 5, 1),
                fases=(3,),
            )
        assert len(resultado) == 2
        assert all(r["_fase_consultada"] == 3 for r in resultado)

    def test_periodo_vazio_nao_gera_erro(self):
        with patch("sucuri.coletores.documentos.coletar_paginado", return_value=[]) as mock_coletar:
            resultado = coletar_documentos_periodo(
                sessao=object(), unidade_gestora="154046",
                data_inicio=date(2025, 5, 10), data_fim=date(2025, 5, 5),  # fim antes do início
                fases=(1, 2, 3),
            )
        assert resultado == []
        mock_coletar.assert_not_called()

    def test_dias_sem_movimento_nao_acumulam_registros(self):
        with patch("sucuri.coletores.documentos.coletar_paginado", return_value=[]):
            resultado = coletar_documentos_periodo(
                sessao=object(), unidade_gestora="154046",
                data_inicio=date(2025, 5, 1), data_fim=date(2025, 5, 5),
                fases=(1, 2, 3),
            )
        assert resultado == []

    def test_parametros_passados_para_coletar_paginado(self):
        with patch("sucuri.coletores.documentos.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_documentos_periodo(
                sessao="sessao-fake", unidade_gestora="154046",
                data_inicio=date(2025, 5, 1), data_fim=date(2025, 5, 1),
                fases=(3,),
            )
        args, _ = mock_coletar.call_args
        sessao_usada, endpoint, params, _rotulo = args
        assert sessao_usada == "sessao-fake"
        assert endpoint == "/despesas/documentos"
        assert params == {"unidadeGestora": "154046", "dataEmissao": "01/05/2025", "fase": 3}
