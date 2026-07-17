"""Testes de sucuri.coletores.sancoes — sem chamadas de rede reais."""

from unittest.mock import patch

import pandas as pd

from sucuri.coletores.sancoes import (
    construir_df_sancoes,
    consultar_sancoes_cnpj,
    consultar_sancoes_lista_cnpjs,
    cruzar_contratos_sancionados,
)


def _sancao_fake(cnpj="00.000.000/0001-00", nome="EMPRESA SANCIONADA",
                  inicio="01/01/2023", fim="01/01/2028"):
    return {
        "sancionado": {"nome": nome, "codigoFormatado": cnpj},
        "orgaoSancionador": {"nomeExibicao": "CGU"},
        "tipoSancao": {"descricaoResumida": "Impedimento de licitar"},
        "dataInicioSancao": inicio,
        "dataFimSancao": fim,
    }


class TestConsultarSancoesCnpj:
    def test_faz_tres_requisicoes(self):
        with patch("sucuri.coletores.sancoes.requisitar", return_value=[]) as mock_req, \
             patch("sucuri.coletores.sancoes.time.sleep"):
            consultar_sancoes_cnpj(sessao="s", cnpj="00.000.000/0001-00")
        assert mock_req.call_count == 3

    def test_retorna_as_tres_fontes(self):
        with patch("sucuri.coletores.sancoes.requisitar", return_value=[]), \
             patch("sucuri.coletores.sancoes.time.sleep"):
            resultado = consultar_sancoes_cnpj(sessao="s", cnpj="00.000.000/0001-00")
        assert set(resultado.keys()) == {"ceis", "cnep", "acordos_leniencia"}


class TestConsultarSancoesListaCnpjs:
    def test_cnpj_sem_sancao_nao_gera_registro(self):
        with patch("sucuri.coletores.sancoes.requisitar", return_value=[]), \
             patch("sucuri.coletores.sancoes.time.sleep"):
            resultado = consultar_sancoes_lista_cnpjs(sessao="s", cnpjs=["1", "2"])
        assert resultado == []

    def test_marca_fonte_e_cnpj_consultado(self):
        # side_effect gera um dict novo por chamada — como uma API real faria
        # (cada requisição HTTP retorna um JSON próprio, nunca o mesmo objeto
        # em memória); usar `return_value` com um objeto mutável compartilhado
        # faria as 3 chamadas colidirem na mesma instância de dict.
        with patch("sucuri.coletores.sancoes.requisitar",
                   side_effect=lambda *a, **k: [_sancao_fake()]), \
             patch("sucuri.coletores.sancoes.time.sleep"):
            resultado = consultar_sancoes_lista_cnpjs(sessao="s", cnpjs=["00.000.000/0001-00"])
        # 3 fontes retornando o mesmo registro fake cada -> 3 registros
        assert len(resultado) == 3
        assert all(r["_cnpj_consultado"] == "00.000.000/0001-00" for r in resultado)
        assert {r["_fonte"] for r in resultado} == {"ceis", "cnep", "acordos_leniencia"}


class TestConstruirDfSancoes:
    def test_lista_vazia(self):
        assert construir_df_sancoes([]).empty

    def test_extrai_campos(self):
        registro = _sancao_fake()
        registro["_fonte"] = "ceis"
        registro["_cnpj_consultado"] = "00.000.000/0001-00"
        df = construir_df_sancoes([registro])
        assert df["cnpjSancionado"].iloc[0] == "00.000.000/0001-00"
        assert df["nomeSancionado"].iloc[0] == "EMPRESA SANCIONADA"
        assert df["fonte"].iloc[0] == "ceis"

    def test_datas_convertidas(self):
        registro = _sancao_fake(inicio="15/03/2022", fim="15/03/2027")
        registro["_fonte"] = "cnep"
        registro["_cnpj_consultado"] = "x"
        df = construir_df_sancoes([registro])
        assert df["dataInicioSancao"].iloc[0] == pd.Timestamp("2022-03-15")


class TestCruzarContratosSancionados:
    def _contrato(self, cnpj, data_assinatura):
        return pd.DataFrame({
            "id": [1], "fornecedorCnpjCpf": [cnpj],
            "dataAssinatura": [pd.Timestamp(data_assinatura)],
            "orgao": ["Órgão X"], "valorFinalCompra": [1000.0],
        })

    def _sancoes(self, cnpj, inicio, fim):
        return pd.DataFrame({
            "cnpjSancionado": [cnpj],
            "dataInicioSancao": [pd.Timestamp(inicio)],
            "dataFimSancao": [pd.Timestamp(fim)] if fim else [pd.NaT],
            "nomeSancionado": ["Empresa"], "fonte": ["ceis"],
        })

    def test_contrato_dentro_do_periodo_de_sancao_e_sinalizado(self):
        contratos = self._contrato("00.000.000/0001-00", "2024-06-01")
        sancoes = self._sancoes("00.000.000/0001-00", "2023-01-01", "2028-01-01")
        resultado = cruzar_contratos_sancionados(contratos, sancoes)
        assert len(resultado) == 1

    def test_contrato_antes_da_sancao_nao_e_sinalizado(self):
        contratos = self._contrato("00.000.000/0001-00", "2022-01-01")
        sancoes = self._sancoes("00.000.000/0001-00", "2023-01-01", "2028-01-01")
        resultado = cruzar_contratos_sancionados(contratos, sancoes)
        assert resultado.empty

    def test_contrato_depois_da_sancao_terminar_nao_e_sinalizado(self):
        contratos = self._contrato("00.000.000/0001-00", "2029-01-01")
        sancoes = self._sancoes("00.000.000/0001-00", "2023-01-01", "2028-01-01")
        resultado = cruzar_contratos_sancionados(contratos, sancoes)
        assert resultado.empty

    def test_sancao_sem_data_fim_continua_valida(self):
        contratos = self._contrato("00.000.000/0001-00", "2099-01-01")
        sancoes = self._sancoes("00.000.000/0001-00", "2023-01-01", None)
        resultado = cruzar_contratos_sancionados(contratos, sancoes)
        assert len(resultado) == 1

    def test_fornecedor_diferente_nao_cruza(self):
        contratos = self._contrato("11.111.111/0001-11", "2024-06-01")
        sancoes = self._sancoes("00.000.000/0001-00", "2023-01-01", "2028-01-01")
        resultado = cruzar_contratos_sancionados(contratos, sancoes)
        assert resultado.empty

    def test_dataframes_vazios_nao_geram_erro(self):
        assert cruzar_contratos_sancionados(pd.DataFrame(), pd.DataFrame()).empty
        assert cruzar_contratos_sancionados(self._contrato("x", "2024-01-01"), pd.DataFrame()).empty
