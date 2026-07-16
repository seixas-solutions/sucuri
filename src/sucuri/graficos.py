"""Estilo e paleta compartilhados para os gráficos da Fase 2 (matplotlib).

Paleta categórica, cores sequenciais/divergentes e cores de interface (ink)
seguem a paleta de referência validada (contraste e distinguibilidade para
daltonismo) usada em todo o projeto — ver o skill `dataviz`. Os gráficos
aqui são estáticos (PNG para markdown/LaTeX), então não se aplicam os
requisitos específicos de páginas web interativas (tooltip, alternância de
tema); usa-se apenas o superfície clara.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

# Ordem fixa — não trocar entre gráficos (identidade de categoria consistente).
PALETA_CATEGORICA = [
    "#2a78d6",  # 1 azul
    "#008300",  # 2 verde
    "#e87ba4",  # 3 magenta
    "#eda100",  # 4 amarelo
    "#1baf7a",  # 5 água
    "#eb6834",  # 6 laranja
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 vermelho
]

COR_SEQUENCIAL = "#2a78d6"          # azul — magnitude, ranking de barra única
COR_DIVERGENTE_POS = "#2a78d6"      # azul
COR_DIVERGENTE_NEG = "#e34948"      # vermelho
COR_DIVERGENTE_NEUTRO = "#f0efec"   # cinza — ponto médio

SUPERFICIE = "#fcfcfb"
TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_MUTED = "#898781"
LINHA_GRADE = "#e1e0d9"
LINHA_BASE = "#c3c2b7"


def aplicar_estilo() -> None:
    """Aplica rcParams consistentes: tinta muted nos eixos, grade sutil,
    sem moldura desnecessária (spines superior/direita removidos)."""
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "axes.edgecolor": LINHA_BASE,
        "axes.labelcolor": TINTA_SECUNDARIA,
        "text.color": TINTA_PRIMARIA,
        "xtick.color": TINTA_MUTED,
        "ytick.color": TINTA_MUTED,
        "grid.color": LINHA_GRADE,
        "grid.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "font.size": 10,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def salvar_figura(fig: plt.Figure, caminho: Path | str, dpi: int = 150) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(caminho, dpi=dpi, facecolor=SUPERFICIE)
    plt.close(fig)
