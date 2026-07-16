"""Testes de sucuri.graficos: paleta e utilidades de estilo."""

import re

import matplotlib
import matplotlib.pyplot as plt

from sucuri.graficos import PALETA_CATEGORICA, aplicar_estilo, salvar_figura

matplotlib.use("Agg")

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestPaleta:
    def test_paleta_tem_oito_cores_em_hex_valido(self):
        assert len(PALETA_CATEGORICA) == 8
        assert all(_HEX.match(c) for c in PALETA_CATEGORICA)

    def test_paleta_sem_cores_repetidas(self):
        assert len(set(PALETA_CATEGORICA)) == len(PALETA_CATEGORICA)


class TestAplicarEstilo:
    def test_nao_levanta_erro(self):
        aplicar_estilo()


class TestSalvarFigura:
    def test_cria_arquivo_png(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        caminho = tmp_path / "sub" / "grafico.png"
        salvar_figura(fig, caminho)
        assert caminho.exists()
        assert caminho.stat().st_size > 0
