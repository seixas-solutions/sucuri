"""Tendência robusta (Theil–Sen) e detecção de resíduos atípicos por série.

Theil-Sen é a mediana das inclinações entre todos os pares de pontos —
muito menos sensível a outliers pontuais que uma regressão linear por
mínimos quadrados, adequada para sinalizar exatamente os pontos que
destoam da tendência (o oposto de uma regressão OLS, que os pontos
puxariam para si).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

FATOR_MAD_PARA_DESVIO_PADRAO = 1.4826  # normaliza MAD para escala de desvio-padrão sob normalidade


def ajustar_theil_sen(anos: np.ndarray, valores: np.ndarray) -> tuple[float, float]:
    """Retorna (inclinação, intercepto) da reta de Theil–Sen."""
    inclinacao, intercepto, _, _ = stats.theilslopes(valores, anos)
    return float(inclinacao), float(intercepto)


def residuos_robustos(anos: np.ndarray, valores: np.ndarray) -> tuple[np.ndarray, float]:
    """Resíduos em relação à tendência de Theil–Sen e o desvio-padrão robusto
    (MAD dos resíduos × 1,4826) usado para padronizá-los."""
    inclinacao, intercepto = ajustar_theil_sen(anos, valores)
    preditos = intercepto + inclinacao * anos
    residuos = valores - preditos
    mad = np.median(np.abs(residuos - np.median(residuos)))
    desvio_robusto = mad * FATOR_MAD_PARA_DESVIO_PADRAO
    return residuos, float(desvio_robusto)


def detectar_eventos_serie(
    df: pd.DataFrame,
    chave: str,
    coluna_ano: str = "ano",
    coluna_valor: str = "pago_real",
    min_anos: int = 8,
    limiar_desvio: float = 2.5,
) -> pd.DataFrame:
    """Ajusta Theil–Sen por série (`chave`) com pelo menos `min_anos` linhas
    elegíveis e retorna os pontos com resíduo padronizado (robusto) acima de
    `limiar_desvio`, ordenados por desvio absoluto decrescente.

    Espera que `df` já esteja restrito a linhas elegíveis (ex.: sem
    `ano_parcial`) — a função não faz essa exclusão sozinha, pois o
    critério de elegibilidade varia por conjunto (ver `analises/05_series.py`).
    """
    eventos = []
    for chave_valor, grupo in df.groupby(chave):
        grupo = grupo.sort_values(coluna_ano)
        if len(grupo) < min_anos:
            continue
        anos = grupo[coluna_ano].to_numpy(dtype=float)
        valores = grupo[coluna_valor].to_numpy(dtype=float)
        residuos, desvio_robusto = residuos_robustos(anos, valores)
        if desvio_robusto == 0:
            # MAD zero: a maioria dos pontos tem o MESMO resíduo (não
            # necessariamente zero — o intercepto de Theil-Sen não é
            # escolhido para zerar resíduos, então o valor "normal" pode
            # ser qualquer constante). Não dá para padronizar por divisão,
            # mas qualquer ponto que destoa desse resíduo dominante já é,
            # por definição, um desvio extremo (não deve ser descartado;
            # ver tests/test_tendencias.py).
            residuo_dominante = np.median(residuos)
            diferenca = residuos - residuo_dominante
            atipico = ~np.isclose(diferenca, 0.0)
            residuo_padronizado = np.zeros_like(residuos)
            residuo_padronizado[atipico] = np.sign(diferenca[atipico]) * np.inf
        else:
            residuo_padronizado = residuos / desvio_robusto
        for i, ano in enumerate(anos):
            if abs(residuo_padronizado[i]) > limiar_desvio:
                eventos.append({
                    chave: chave_valor,
                    coluna_ano: int(ano),
                    coluna_valor: valores[i],
                    "residuo": residuos[i],
                    "desvio_padronizado": residuo_padronizado[i],
                    "n_anos_serie": len(grupo),
                })
    if not eventos:
        return pd.DataFrame(columns=[chave, coluna_ano, coluna_valor, "residuo", "desvio_padronizado", "n_anos_serie"])
    resultado = pd.DataFrame(eventos)
    return resultado.reindex(resultado["desvio_padronizado"].abs().sort_values(ascending=False).index).reset_index(drop=True)
