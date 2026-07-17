"""Testes de sucuri.coletores.contratos — sem chamadas de rede reais."""

import math
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from sucuri.coletores.contratos import (
    coletar_contratos_orgao,
    construir_df_contratos,
    detectar_fracionamento,
    indice_herfindahl,
)


def _contrato_fake(
    codigo_orgao="26277", fornecedor_cnpj="00.000.000/0001-00", fornecedor_nome="EMPRESA X",
    modalidade="Tomada de Preços", valor_inicial=1000.0, valor_final=1000.0,
    inicio="2024-01-01", fim="2024-12-31", numero_processo_compra="23109.000001/2024-01",
):
    return {
        "id": 1,
        "numero": "1/2024",
        "numeroProcesso": "Sem informação",  # campo raiz: sempre vazio na API real
        "objeto": "objeto de teste",
        "modalidadeCompra": modalidade,
        "compra": {"numero": "1/2024", "numeroProcesso": numero_processo_compra},
        "unidadeGestora": {"orgaoVinculado": {"codigoSIAFI": codigo_orgao, "nome": "Órgão Teste"}},
        "fornecedor": {"cnpjFormatado": fornecedor_cnpj, "nome": fornecedor_nome, "tipo": "Entidade Privada"},
        "dataAssinatura": "2023-12-20",
        "dataInicioVigencia": inicio,
        "dataFimVigencia": fim,
        "valorInicialCompra": valor_inicial,
        "valorFinalCompra": valor_final,
    }


class TestColetarContratosOrgao:
    def test_parametros_corretos(self):
        with patch("sucuri.coletores.contratos.coletar_paginado", return_value=[]) as mock_coletar:
            coletar_contratos_orgao(
                sessao="s", codigo_orgao="26277",
                data_inicial=date(2018, 1, 1), data_final=date(2025, 12, 31),
            )
        args, _ = mock_coletar.call_args
        _sessao, endpoint, params, _rotulo = args
        assert endpoint == "/contratos"
        assert params == {"codigoOrgao": "26277", "dataInicial": "01/01/2018", "dataFinal": "31/12/2025"}


class TestConstruirDfContratos:
    def test_lista_vazia_retorna_df_vazio(self):
        assert construir_df_contratos([]).empty

    def test_extrai_campos_aninhados(self):
        df = construir_df_contratos([_contrato_fake()])
        assert df["codigoOrgao"].iloc[0] == "26277"
        assert df["fornecedorCnpjCpf"].iloc[0] == "00.000.000/0001-00"

    def test_numero_processo_vem_do_campo_aninhado_em_compra(self):
        # Achado da tarefa 3.3: o campo raiz `numeroProcesso` vem sempre
        # "Sem informação" na API real — o valor correto está em
        # `compra.numeroProcesso`. Regressão desse bug específico.
        df = construir_df_contratos([_contrato_fake(numero_processo_compra="23109.999999/2024-99")])
        assert df["numeroProcesso"].iloc[0] == "23109.999999/2024-99"

    def test_numero_processo_cai_para_campo_raiz_se_compra_ausente(self):
        registro = _contrato_fake()
        del registro["compra"]
        registro["numeroProcesso"] = "valor-do-campo-raiz"
        df = construir_df_contratos([registro])
        assert df["numeroProcesso"].iloc[0] == "valor-do-campo-raiz"

    def test_valor_aditivado_calculado(self):
        df = construir_df_contratos([_contrato_fake(valor_inicial=1000.0, valor_final=1200.0)])
        assert df["valor_aditivado"].iloc[0] == pytest.approx(200.0)
        assert df["pct_aditivado"].iloc[0] == pytest.approx(0.2)

    def test_sem_aditivo_valor_aditivado_zero(self):
        df = construir_df_contratos([_contrato_fake(valor_inicial=1000.0, valor_final=1000.0)])
        assert df["valor_aditivado"].iloc[0] == pytest.approx(0.0)

    def test_prazo_em_dias(self):
        df = construir_df_contratos([_contrato_fake(inicio="2024-01-01", fim="2024-01-31")])
        assert df["prazo_dias"].iloc[0] == 30

    def test_detecta_dispensa(self):
        df = construir_df_contratos([_contrato_fake(modalidade="Dispensa de Licitação")])
        assert bool(df["eh_dispensa_ou_inexigibilidade"].iloc[0]) is True

    def test_detecta_inexigibilidade(self):
        df = construir_df_contratos([_contrato_fake(modalidade="Inexigibilidade de Licitação")])
        assert bool(df["eh_dispensa_ou_inexigibilidade"].iloc[0]) is True

    def test_modalidade_normal_nao_e_dispensa(self):
        df = construir_df_contratos([_contrato_fake(modalidade="Pregão Eletrônico")])
        assert bool(df["eh_dispensa_ou_inexigibilidade"].iloc[0]) is False

    def test_valorInicialCompra_zero_produz_pct_aditivado_nan(self):
        df = construir_df_contratos([_contrato_fake(valor_inicial=0.0, valor_final=100.0)])
        assert math.isnan(df["pct_aditivado"].iloc[0])


class TestIndiceHerfindahl:
    def test_monopolio_hhi_maximo(self):
        df = pd.DataFrame({
            "codigoOrgao": ["A", "A"],
            "fornecedorCnpjCpf": ["F1", "F1"],
            "valorFinalCompra": [100.0, 200.0],
        })
        resultado = indice_herfindahl(df)
        assert resultado["hhi_fornecedores"].iloc[0] == pytest.approx(10000.0)
        assert resultado["n_fornecedores"].iloc[0] == 1

    def test_dois_fornecedores_iguais_hhi_5000(self):
        df = pd.DataFrame({
            "codigoOrgao": ["A", "A"],
            "fornecedorCnpjCpf": ["F1", "F2"],
            "valorFinalCompra": [100.0, 100.0],
        })
        resultado = indice_herfindahl(df)
        assert resultado["hhi_fornecedores"].iloc[0] == pytest.approx(5000.0)

    def test_muitos_fornecedores_pequenos_hhi_baixo(self):
        df = pd.DataFrame({
            "codigoOrgao": ["A"] * 10,
            "fornecedorCnpjCpf": [f"F{i}" for i in range(10)],
            "valorFinalCompra": [100.0] * 10,
        })
        resultado = indice_herfindahl(df)
        assert resultado["hhi_fornecedores"].iloc[0] == pytest.approx(1000.0)

    def test_grupos_diferentes_calculados_separadamente(self):
        df = pd.DataFrame({
            "codigoOrgao": ["A", "A", "B", "B"],
            "fornecedorCnpjCpf": ["F1", "F1", "F2", "F3"],
            "valorFinalCompra": [100.0, 100.0, 100.0, 100.0],
        })
        resultado = indice_herfindahl(df).set_index("codigoOrgao")
        assert resultado.loc["A", "hhi_fornecedores"] == pytest.approx(10000.0)
        assert resultado.loc["B", "hhi_fornecedores"] == pytest.approx(5000.0)


def _df_dispensas(n: int, valor: float, fornecedor="F1", ano=2024, codigo_orgao="26236"):
    return pd.DataFrame({
        "id": range(n),
        "codigoOrgao": [codigo_orgao] * n,
        "orgao": ["Órgão Teste"] * n,
        "fornecedorCnpjCpf": [fornecedor] * n,
        "fornecedorNome": ["Fornecedor Teste"] * n,
        "ano": [ano] * n,
        "eh_dispensa_ou_inexigibilidade": [True] * n,
        "valorFinalCompra": [valor] * n,
    })


class TestDetectarFracionamento:
    def test_poucas_dispensas_pequenas_nao_sinaliza(self):
        df = _df_dispensas(n=1, valor=10_000.0)
        resultado = detectar_fracionamento(df, min_ocorrencias=2, limiar_valor=50_000.0)
        assert resultado.empty

    def test_varias_dispensas_pequenas_somando_acima_do_limiar_sinaliza(self):
        df = _df_dispensas(n=3, valor=20_000.0)  # 3 x 20k = 60k > limiar 50k
        resultado = detectar_fracionamento(df, min_ocorrencias=2, limiar_valor=50_000.0)
        assert len(resultado) == 1
        assert resultado["n_contratos"].iloc[0] == 3
        assert resultado["valor_somado"].iloc[0] == pytest.approx(60_000.0)

    def test_contrato_unico_acima_do_limiar_nao_conta_como_fracionamento(self):
        # eh_dispensa mas já está sozinho acima do limiar -> filtrado antes
        # de contar ocorrências (não é "vários pequenos", é um só grande).
        df = _df_dispensas(n=1, valor=80_000.0)
        resultado = detectar_fracionamento(df, min_ocorrencias=2, limiar_valor=50_000.0)
        assert resultado.empty

    def test_nao_dispensa_e_ignorado(self):
        df = _df_dispensas(n=3, valor=20_000.0)
        df["eh_dispensa_ou_inexigibilidade"] = False
        resultado = detectar_fracionamento(df, min_ocorrencias=2, limiar_valor=50_000.0)
        assert resultado.empty

    def test_fornecedores_diferentes_nao_se_somam(self):
        df1 = _df_dispensas(n=2, valor=20_000.0, fornecedor="F1")
        df2 = _df_dispensas(n=2, valor=20_000.0, fornecedor="F2")
        df = pd.concat([df1, df2], ignore_index=True)
        resultado = detectar_fracionamento(df, min_ocorrencias=2, limiar_valor=50_000.0)
        # cada fornecedor sozinho soma 40k < 50k -> nenhum sinalizado
        assert resultado.empty

    def test_df_vazio_nao_gera_erro(self):
        df = pd.DataFrame(columns=["id", "codigoOrgao", "orgao", "fornecedorCnpjCpf",
                                     "fornecedorNome", "ano", "eh_dispensa_ou_inexigibilidade",
                                     "valorFinalCompra"])
        resultado = detectar_fracionamento(df)
        assert resultado.empty
