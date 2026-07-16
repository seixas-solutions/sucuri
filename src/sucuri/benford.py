"""Lei de Benford: distribuição de primeiro/segundo dígito significativo.

Referência dos limiares de conformidade (MAD, Nigrini 2012, "Benford's Law:
Applications for Forensic Accounting, Auditing, and Fraud Detection"):
diferentes por teste porque o número de categorias difere (9 para o
primeiro dígito, 10 para o segundo).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

# (limite_superior_close, limite_superior_aceitavel, limite_superior_marginal)
# acima do último limite -> "Não conformidade".
LIMIARES_MAD = {
    "primeiro": (0.006, 0.012, 0.015),
    "segundo": (0.008, 0.010, 0.012),
}

AMOSTRA_MINIMA_CONCLUSIVA = 300


def primeiro_digito(serie: pd.Series) -> pd.Series:
    """Primeiro dígito significativo (1–9) de cada valor positivo da série."""
    valores = serie.dropna()
    valores = valores[valores > 0]
    expoente = valores.apply(lambda v: math.floor(math.log10(v)))
    return (valores / (10.0 ** expoente)).astype(int)


def segundo_digito(serie: pd.Series) -> pd.Series:
    """Segundo dígito (0–9) de cada valor positivo com pelo menos 2 algarismos
    significativos (valores no intervalo [1, 10) — um único algarismo — são
    descartados, pois não têm segundo dígito)."""
    valores = serie.dropna()
    valores = valores[valores > 0]
    expoente = valores.apply(lambda v: math.floor(math.log10(v)))
    normalizado = valores / (10.0 ** expoente)  # em [1, 10)
    segundo = np.floor(normalizado * 10) % 10
    return segundo.astype(int)


def distribuicao_esperada(posicao: str) -> pd.Series:
    """Probabilidade esperada pela Lei de Benford para cada dígito."""
    if posicao == "primeiro":
        digitos = range(1, 10)
        probs = [math.log10(1 + 1 / d) for d in digitos]
    elif posicao == "segundo":
        digitos = range(0, 10)
        probs = [sum(math.log10(1 + 1 / (10 * k + d)) for k in range(1, 10)) for d in digitos]
    else:
        raise ValueError("posicao deve ser 'primeiro' ou 'segundo'")
    return pd.Series(probs, index=list(digitos))


def mad_nigrini(prop_observada: pd.Series, prop_esperada: pd.Series) -> float:
    """Mean Absolute Deviation entre proporções observadas e esperadas."""
    return float((prop_observada - prop_esperada).abs().mean())


def classificar_mad(mad: float, posicao: str) -> str:
    close, aceitavel, marginal = LIMIARES_MAD[posicao]
    if mad < close:
        return "Conformidade próxima"
    if mad < aceitavel:
        return "Conformidade aceitável"
    if mad < marginal:
        return "Conformidade marginal"
    return "Não conformidade"


def aplicar_benford(serie: pd.Series, posicao: str = "primeiro") -> dict:
    """Roda o teste de Benford (primeiro ou segundo dígito) sobre `serie`.

    Retorna contagens/proporções observadas e esperadas, estatística
    qui-quadrado (com p-valor) e classificação MAD (Nigrini). Amostras
    menores que `AMOSTRA_MINIMA_CONCLUSIVA` são sinalizadas como
    inconclusivas (`amostra_suficiente=False`) — o resultado ainda é
    calculado, mas não deve ser interpretado como conformidade/desvio.
    """
    digitos = primeiro_digito(serie) if posicao == "primeiro" else segundo_digito(serie)
    n = len(digitos)
    esperada_prob = distribuicao_esperada(posicao)

    contagem_obs = digitos.value_counts().reindex(esperada_prob.index, fill_value=0).sort_index()
    prop_obs = contagem_obs / n if n else contagem_obs.astype(float)
    contagem_esp = esperada_prob * n

    chi2, p_valor = stats.chisquare(f_obs=contagem_obs.values, f_exp=contagem_esp.values) if n else (float("nan"), float("nan"))
    mad = mad_nigrini(prop_obs, esperada_prob) if n else float("nan")

    return {
        "n": n,
        "posicao": posicao,
        "contagem_observada": contagem_obs,
        "proporcao_observada": prop_obs,
        "proporcao_esperada": esperada_prob,
        "chi2": chi2,
        "p_valor": p_valor,
        "mad": mad,
        "classificacao": classificar_mad(mad, posicao) if n else "Sem dados",
        "amostra_suficiente": n >= AMOSTRA_MINIMA_CONCLUSIVA,
    }
