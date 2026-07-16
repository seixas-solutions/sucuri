"""Testes de sucuri.deflacao: índice encadeado e deflacionamento de valores."""

import math

import pandas as pd
import pytest

from sucuri.deflacao import carregar_ipca, construir_indice_encadeado, deflacionar


class TestCarregarIpca:
    def test_arquivo_inexistente_levanta_erro_claro(self, tmp_path):
        caminho = tmp_path / "nao_existe.csv"
        with pytest.raises(FileNotFoundError, match="EXTERNAL.md"):
            carregar_ipca(caminho)

    def test_carrega_csv_valido(self, tmp_path):
        caminho = tmp_path / "ipca.csv"
        pd.DataFrame({"ano": [2014, 2015], "ipca_acumulado_pct": [6.4, 10.7]}).to_csv(
            caminho, index=False)
        df = carregar_ipca(caminho)
        assert list(df["ano"]) == [2014, 2015]


class TestIndiceEncadeado:
    def test_fator_de_dois_anos_conhecido(self):
        ipca = pd.DataFrame({"ano": [2020, 2021], "ipca_acumulado_pct": [10.0, 20.0]})
        indice = construir_indice_encadeado(ipca)
        # fator acumulado de 2020->2021 = 1.10 * 1.20 = 1.32 (em relação ao ano anterior a 2020)
        assert indice.loc[2020] == pytest.approx(1.10)
        assert indice.loc[2021] == pytest.approx(1.10 * 1.20)
        # razão entre os dois anos é o que importa para deflacionar
        assert indice.loc[2021] / indice.loc[2020] == pytest.approx(1.20)

    def test_ordem_de_entrada_nao_importa(self):
        ipca_ordenado = pd.DataFrame({"ano": [2020, 2021, 2022], "ipca_acumulado_pct": [5, 10, 15]})
        ipca_embaralhado = pd.DataFrame({"ano": [2022, 2020, 2021], "ipca_acumulado_pct": [15, 5, 10]})
        i1 = construir_indice_encadeado(ipca_ordenado)
        i2 = construir_indice_encadeado(ipca_embaralhado)
        assert i1.loc[2022] == pytest.approx(i2.loc[2022])


class TestDeflacionar:
    def _indice_simples(self):
        # ano-base 2021 com o dobro do índice de 2020 -> deflacionar 2020 para
        # 2021 deve DOBRAR o valor nominal (fator de correção conhecido).
        return pd.Series({2020: 1.0, 2021: 2.0}, name="indice_ipca")

    def test_ano_base_permanece_igual(self):
        df = pd.DataFrame({"ano": [2021], "pago": [100.0]})
        resultado = deflacionar(df, self._indice_simples(), ano_base=2021, colunas=["pago"])
        assert resultado["pago_real"].iloc[0] == pytest.approx(100.0)

    def test_ano_anterior_e_corrigido_para_cima_com_fator_conhecido(self):
        df = pd.DataFrame({"ano": [2020], "pago": [100.0]})
        resultado = deflacionar(df, self._indice_simples(), ano_base=2021, colunas=["pago"])
        assert resultado["pago_real"].iloc[0] == pytest.approx(200.0)

    def test_multiplas_colunas_deflacionadas(self):
        df = pd.DataFrame({"ano": [2020], "empenhado": [50.0], "pago": [100.0]})
        resultado = deflacionar(df, self._indice_simples(), ano_base=2021,
                                  colunas=["empenhado", "pago"])
        assert resultado["empenhado_real"].iloc[0] == pytest.approx(100.0)
        assert resultado["pago_real"].iloc[0] == pytest.approx(200.0)

    def test_ano_fora_do_indice_gera_nan_sem_erro(self):
        df = pd.DataFrame({"ano": [1999], "pago": [100.0]})
        resultado = deflacionar(df, self._indice_simples(), ano_base=2021, colunas=["pago"])
        assert math.isnan(resultado["pago_real"].iloc[0])

    def test_ano_base_ausente_no_indice_levanta_erro(self):
        df = pd.DataFrame({"ano": [2020], "pago": [100.0]})
        with pytest.raises(ValueError, match="2099"):
            deflacionar(df, self._indice_simples(), ano_base=2099, colunas=["pago"])

    def test_coluna_original_preservada(self):
        df = pd.DataFrame({"ano": [2020], "pago": [100.0]})
        resultado = deflacionar(df, self._indice_simples(), ano_base=2021, colunas=["pago"])
        assert resultado["pago"].iloc[0] == 100.0
