"""Testes de sucuri.coletores.cartoes — sem chamadas de rede reais."""

from unittest.mock import patch

from sucuri.coletores.cartoes import (
    coletar_cartoes,
    construir_df_cartoes,
    resumo_red_flags_por_orgao,
    valores_repetidos_mesmo_portador,
)


def _transacao_fake(codigo_orgao="26277", data="15/06/2024", valor="150,00",
                     estabelecimento="SUPERMERCADO X", portador_cpf="***.111.111-**",
                     portador_nome="FULANO"):
    return {
        "id": 1,
        "dataTransacao": data,
        "valorTransacao": valor,
        "estabelecimento": {"nome": estabelecimento, "cnpjFormatado": "00.000.000/0001-00"},
        "unidadeGestora": {"orgaoVinculado": {"codigoSIAFI": codigo_orgao, "nome": "Órgão Teste"}},
        "portador": {"cpfFormatado": portador_cpf, "nome": portador_nome},
    }


class TestColetarCartoes:
    def test_parametros_corretos(self):
        with patch("sucuri.coletores.cartoes.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_cartoes(sessao="s", codigo_orgao="26277", ano_inicio=2023, ano_fim=2025)
        args, _ = mock_coletar.call_args
        _sessao, endpoint, params, _rotulo = args
        assert endpoint == "/cartoes"
        assert params == {
            "codigoOrgao": "26277", "mesExtratoInicio": "01/2023",
            "mesExtratoFim": "12/2025", "tipoCartao": 1,
        }


class TestConstruirDfCartoes:
    def test_lista_vazia(self):
        assert construir_df_cartoes([]).empty

    def test_extrai_valor_formato_brasileiro(self):
        df = construir_df_cartoes([_transacao_fake(valor="1.234,56")])
        assert df["valor"].iloc[0] == 1234.56

    def test_detecta_fim_de_semana_sabado(self):
        df = construir_df_cartoes([_transacao_fake(data="15/06/2024")])  # sábado
        assert bool(df["eh_fim_de_semana"].iloc[0]) is True

    def test_dia_de_semana_nao_e_fim_de_semana(self):
        df = construir_df_cartoes([_transacao_fake(data="17/06/2024")])  # segunda
        assert bool(df["eh_fim_de_semana"].iloc[0]) is False

    def test_detecta_dezembro(self):
        df = construir_df_cartoes([_transacao_fake(data="20/12/2024")])
        assert bool(df["eh_dezembro"].iloc[0]) is True

    def test_detecta_provavel_saque_por_nome_estabelecimento(self):
        df = construir_df_cartoes([_transacao_fake(estabelecimento="BANCO DO BRASIL SA")])
        assert bool(df["eh_provavel_saque"].iloc[0]) is True

    def test_supermercado_nao_e_saque(self):
        df = construir_df_cartoes([_transacao_fake(estabelecimento="SUPERMERCADO X")])
        assert bool(df["eh_provavel_saque"].iloc[0]) is False


class TestResumoRedFlagsPorOrgao:
    def test_df_vazio(self):
        assert resumo_red_flags_por_orgao(construir_df_cartoes([])).empty

    def test_agrega_por_orgao(self):
        registros = [
            _transacao_fake(codigo_orgao="26277", valor="100,00", data="15/06/2024"),
            _transacao_fake(codigo_orgao="26277", valor="200,00", data="16/06/2024"),
        ]
        df = construir_df_cartoes(registros)
        resumo = resumo_red_flags_por_orgao(df)
        assert len(resumo) == 1
        assert resumo["n_transacoes"].iloc[0] == 2
        assert resumo["valor_total"].iloc[0] == 300.0


class TestValoresRepetidosMesmoPortador:
    def test_poucas_repeticoes_nao_aparece(self):
        registros = [_transacao_fake(valor="150,00") for _ in range(2)]
        df = construir_df_cartoes(registros)
        resultado = valores_repetidos_mesmo_portador(df, min_ocorrencias=3)
        assert resultado.empty

    def test_repeticoes_suficientes_aparecem(self):
        registros = [_transacao_fake(valor="150,00") for _ in range(4)]
        df = construir_df_cartoes(registros)
        resultado = valores_repetidos_mesmo_portador(df, min_ocorrencias=3)
        assert len(resultado) == 1
        assert resultado["n_ocorrencias"].iloc[0] == 4

    def test_valores_diferentes_nao_se_somam(self):
        registros = [_transacao_fake(valor="150,00"), _transacao_fake(valor="200,00"),
                     _transacao_fake(valor="150,00")]
        df = construir_df_cartoes(registros)
        resultado = valores_repetidos_mesmo_portador(df, min_ocorrencias=2)
        assert len(resultado) == 1
        assert resultado["valor"].iloc[0] == 150.0
