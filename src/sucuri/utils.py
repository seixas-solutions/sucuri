"""Utilidades genéricas: conversão de valores e classificação de instituições."""

from __future__ import annotations

import math

import pandas as pd


def brl_para_float(valor: str | float | None) -> float:
    """Converte '1.059.473.395,24' -> 1059473395.24. Vazio/None -> 0.0."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return math.nan


def razao_segura(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Divisão elemento a elemento retornando NaN quando o denominador é 0."""
    den = denominador.where(denominador != 0)
    return numerador / den


def classificar_instituicao(descricao: str) -> str:
    """Classifica o órgão do MEC em categorias para comparação entre pares."""
    d = (descricao or "").upper()
    if "HOSPITAL" in d or "SERVIÇOS HOSPITALARES" in d or "SERVICOS HOSPITALARES" in d:
        return "Hospitalar (EBSERH)"
    if "UNIVERSIDADE" in d:
        return "Universidade Federal"
    if any(t in d for t in ("INSTITUTO FEDERAL", "CENTRO FEDERAL", "CEFET", "ESCOLA TÉCNICA", "ESCOLA TECNICA")):
        return "Instituto/CEFET/Escola Técnica"
    if "APERFEIÇOAMENTO" in d or "APERFEICOAMENTO" in d or "CAPES" in d:
        return "CAPES"
    if "FUNDO" in d or "FINANCIAMENTO AO ESTUDANTE" in d:
        return "Fundo (FNDE/FIES)"
    if "COLÉGIO" in d or "COLEGIO" in d:
        return "Educação Básica"
    return "Outros / Administração"
