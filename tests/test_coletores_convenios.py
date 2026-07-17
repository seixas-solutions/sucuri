"""Testes de sucuri.coletores.convenios — sem chamadas de rede reais."""

from datetime import date
from unittest.mock import patch

import pytest

from sucuri.coletores.convenios import (
    coletar_convenios,
    construir_df_convenios,
    convenentes_multiplos_inadimplentes,
    top_convenentes,
)


def _convenio_fake(cnpj="00.000.000/0001-00", nome="PREFEITURA X", situacao="ADIMPLENTE",
                    valor=100000.0, tipo="Administração Pública Municipal", localidade="Municipal"):
    return {
        "id": 1,
        "situacao": situacao,
        "convenente": {"cnpjFormatado": cnpj, "nome": nome, "tipo": tipo},
        "localidadePessoa": {"descricao": localidade},
        "municipioConvenente": {"uf": {"sigla": "SP"}},
        "orgao": {"codigoSIAFI": "26298", "nome": "FNDE"},
        "dataInicioVigencia": "2023-01-01",
        "dataFinalVigencia": "2024-01-01",
        "valor": valor,
        "valorLiberado": valor,
        "valorContrapartida": 0.0,
    }


class TestColetarConvenios:
    def test_parametros_corretos(self):
        with patch("sucuri.coletores.convenios.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_convenios(sessao="s", data_inicial=date(2018, 1, 1), data_final=date(2025, 12, 31))
        args, _ = mock_coletar.call_args
        _sessao, endpoint, params, _rotulo = args
        assert endpoint == "/convenios"
        assert params == {"codigoOrgao": "26000", "dataInicial": "01/01/2018", "dataFinal": "31/12/2025"}


class TestConstruirDfConvenios:
    def test_lista_vazia(self):
        assert construir_df_convenios([]).empty

    def test_extrai_campos(self):
        df = construir_df_convenios([_convenio_fake()])
        assert df["convenenteCnpjCpf"].iloc[0] == "00.000.000/0001-00"
        assert df["ano"].iloc[0] == 2023

    def test_detecta_inadimplente(self):
        df = construir_df_convenios([_convenio_fake(situacao="INADIMPLENTE NO SICONV")])
        assert bool(df["eh_inadimplente"].iloc[0]) is True

    def test_adimplente_nao_e_inadimplente(self):
        df = construir_df_convenios([_convenio_fake(situacao="ADIMPLENTE")])
        assert bool(df["eh_inadimplente"].iloc[0]) is False


class TestConvenentesMultiplosInadimplentes:
    def test_um_inadimplente_nao_aparece(self):
        df = construir_df_convenios([_convenio_fake(situacao="INADIMPLENTE")])
        resultado = convenentes_multiplos_inadimplentes(df, min_inadimplentes=2)
        assert resultado.empty

    def test_dois_ou_mais_aparecem(self):
        registros = [_convenio_fake(situacao="INADIMPLENTE") for _ in range(3)]
        df = construir_df_convenios(registros)
        resultado = convenentes_multiplos_inadimplentes(df, min_inadimplentes=2)
        assert len(resultado) == 1
        assert resultado["n_inadimplentes"].iloc[0] == 3

    def test_df_vazio(self):
        assert convenentes_multiplos_inadimplentes(construir_df_convenios([])).empty


class TestTopConvenentes:
    def test_ordenado_por_valor_desc(self):
        registros = [
            _convenio_fake(cnpj="1", nome="A", valor=100.0),
            _convenio_fake(cnpj="2", nome="B", valor=500.0),
        ]
        df = construir_df_convenios(registros)
        resultado = top_convenentes(df, n=20)
        assert resultado["convenenteNome"].iloc[0] == "B"

    def test_soma_valores_do_mesmo_convenente(self):
        registros = [
            _convenio_fake(cnpj="1", nome="A", valor=100.0),
            _convenio_fake(cnpj="1", nome="A", valor=200.0),
        ]
        df = construir_df_convenios(registros)
        resultado = top_convenentes(df, n=20)
        assert resultado["valor_total"].iloc[0] == pytest.approx(300.0)
        assert resultado["n_convenios"].iloc[0] == 2

    def test_conta_inadimplentes_por_convenente(self):
        registros = [
            _convenio_fake(cnpj="1", nome="A", situacao="ADIMPLENTE"),
            _convenio_fake(cnpj="1", nome="A", situacao="INADIMPLENTE"),
        ]
        df = construir_df_convenios(registros)
        resultado = top_convenentes(df, n=20)
        assert resultado["n_inadimplentes"].iloc[0] == 1

    def test_df_vazio_retorna_vazio(self):
        assert top_convenentes(construir_df_convenios([])).empty
