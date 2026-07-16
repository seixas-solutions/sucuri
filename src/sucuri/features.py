"""Engenharia de variáveis e construção dos painéis de despesas."""

from __future__ import annotations

import pandas as pd

from sucuri.utils import brl_para_float, classificar_instituicao, razao_segura


# --------------------------------------------------------------------------- #
# (A) Painel funcional-programático — função 12 / subfunção 364
# --------------------------------------------------------------------------- #
def construir_df_funcional(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if df.empty:
        return df

    for col in ("empenhado", "liquidado", "pago"):
        df[col] = df[col].map(brl_para_float)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["chave_serie"] = df["codigoPrograma"].astype(str) + "-" + df["codigoAcao"].astype(str)

    df = indicadores_execucao(df)
    df = features_serie_temporal(df, chave="chave_serie")
    df = consolidar_flags(df)

    colunas = [
        "ano", "codigoFuncao", "funcao", "codigoSubfuncao", "subfuncao",
        "codigoPrograma", "programa", "codigoAcao", "acao", "chave_serie",
        "empenhado", "liquidado", "pago",
        "taxa_liquidacao", "taxa_pagamento", "valor_a_liquidar", "restos_a_pagar",
        "variacao_pago_aa", "zscore_pago", "zscore_robusto_pago",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado",
        "flag_valor_negativo", "flag_anomalia_zscore", "flag_anomalia_robusto",
        "flag_salto_anual", "flag_anomalia",
    ]
    return df[[c for c in colunas if c in df.columns]]


# --------------------------------------------------------------------------- #
# (B) Painel por instituição — órgãos do MEC
# --------------------------------------------------------------------------- #
def construir_df_instituicao(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if df.empty:
        return df

    for col in ("empenhado", "liquidado", "pago"):
        df[col] = df[col].map(brl_para_float)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["chave_serie"] = df["codigoOrgao"].astype(str)
    df["tipo_instituicao"] = df["orgao"].map(classificar_instituicao)

    df = indicadores_execucao(df)
    # Série temporal por instituição (evolução ao longo dos anos).
    df = features_serie_temporal(df, chave="chave_serie")

    # Comparação ENTRE PARES: z-score do valor pago entre instituições do mesmo
    # tipo, no mesmo ano. Sinaliza instituição atípica frente aos seus pares.
    g = df.groupby(["ano", "tipo_instituicao"])["pago"]
    df["zscore_pago_entre_pares"] = (df["pago"] - g.transform("mean")) / g.transform("std").replace(0, pd.NA)
    df["flag_atipico_entre_pares"] = df["zscore_pago_entre_pares"].abs() > 3

    df = consolidar_flags(df, extra=["flag_atipico_entre_pares"])

    colunas = [
        "ano", "codigoOrgaoSuperior", "orgaoSuperior",
        "codigoOrgao", "orgao", "tipo_instituicao", "chave_serie",
        "empenhado", "liquidado", "pago",
        "taxa_liquidacao", "taxa_pagamento", "valor_a_liquidar", "restos_a_pagar",
        "variacao_pago_aa", "zscore_pago", "zscore_robusto_pago", "zscore_pago_entre_pares",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado",
        "flag_valor_negativo", "flag_anomalia_zscore", "flag_anomalia_robusto",
        "flag_salto_anual", "flag_atipico_entre_pares", "flag_anomalia",
    ]
    return df[[c for c in colunas if c in df.columns]]


# --------------------------------------------------------------------------- #
# Engenharia de variáveis compartilhada
# --------------------------------------------------------------------------- #
def indicadores_execucao(df: pd.DataFrame) -> pd.DataFrame:
    df["taxa_liquidacao"] = razao_segura(df["liquidado"], df["empenhado"])
    df["taxa_pagamento"] = razao_segura(df["pago"], df["empenhado"])
    df["valor_a_liquidar"] = df["empenhado"] - df["liquidado"]
    df["restos_a_pagar"] = df["liquidado"] - df["pago"]
    df["flag_pago_maior_empenhado"] = df["pago"] > df["empenhado"] + 0.005
    df["flag_liquidado_maior_empenhado"] = df["liquidado"] > df["empenhado"] + 0.005
    df["flag_valor_negativo"] = (df["empenhado"] < 0) | (df["liquidado"] < 0) | (df["pago"] < 0)
    return df


def features_serie_temporal(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Variação anual e z-scores (clássico e robusto) do valor pago por série."""
    df = df.sort_values([chave, "ano"]).reset_index(drop=True)
    grupo = df.groupby(chave)["pago"]

    df["variacao_pago_aa"] = grupo.pct_change()

    media, desvio = grupo.transform("mean"), grupo.transform("std")
    df["zscore_pago"] = (df["pago"] - media) / desvio.replace(0, pd.NA)

    mediana = grupo.transform("median")
    mad = grupo.transform(lambda s: (s - s.median()).abs().median())
    df["zscore_robusto_pago"] = 0.6745 * (df["pago"] - mediana) / mad.replace(0, pd.NA)

    df["flag_anomalia_zscore"] = df["zscore_pago"].abs() > 3
    df["flag_anomalia_robusto"] = df["zscore_robusto_pago"].abs() > 3.5
    df["flag_salto_anual"] = df["variacao_pago_aa"].abs() > 1.0
    return df


def consolidar_flags(df: pd.DataFrame, extra: list[str] | None = None) -> pd.DataFrame:
    flags = [
        "flag_anomalia_zscore", "flag_anomalia_robusto", "flag_salto_anual",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado", "flag_valor_negativo",
    ] + (extra or [])
    consolidado = pd.Series(False, index=df.index)
    for f in flags:
        consolidado |= df[f].fillna(False)
    df["flag_anomalia"] = consolidado
    return df
