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
    df = zscore_entre_pares(df)

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


def features_serie_temporal(df: pd.DataFrame, chave: str, coluna_valor: str = "pago") -> pd.DataFrame:
    """Variação anual e z-scores (clássico e robusto) por série.

    `coluna_valor` indica qual coluna monetária usar como base do cálculo
    (por padrão `pago`, nominal — comportamento original). A partir da
    tarefa 1.2, o pipeline de análise chama esta função com
    `coluna_valor="pago_real"` (deflacionado), pois comparar valores
    nominais entre anos confunde inflação com variação real de gasto; os
    nomes das colunas de saída (`variacao_pago_aa`, `zscore_pago`, ...)
    permanecem os mesmos independentemente da coluna de entrada — o
    significado ("com base em qual valor") deve ser inferido do contexto
    de chamada e documentado no relatório correspondente.
    """
    df = df.sort_values([chave, "ano"]).reset_index(drop=True)
    grupo = df.groupby(chave)[coluna_valor]

    df["variacao_pago_aa"] = grupo.pct_change()

    media, desvio = grupo.transform("mean"), grupo.transform("std")
    df["zscore_pago"] = (df[coluna_valor] - media) / desvio.replace(0, pd.NA)

    mediana = grupo.transform("median")
    mad = grupo.transform(lambda s: (s - s.median()).abs().median())
    df["zscore_robusto_pago"] = 0.6745 * (df[coluna_valor] - mediana) / mad.replace(0, pd.NA)

    df["flag_anomalia_zscore"] = df["zscore_pago"].abs() > 3
    df["flag_anomalia_robusto"] = df["zscore_robusto_pago"].abs() > 3.5
    df["flag_salto_anual"] = df["variacao_pago_aa"].abs() > 1.0
    return df


def zscore_entre_pares(
    df: pd.DataFrame,
    coluna_valor: str = "pago",
    chave_grupo: tuple[str, str] = ("ano", "tipo_instituicao"),
) -> pd.DataFrame:
    """Z-score de `coluna_valor` entre instituições do mesmo grupo (por
    padrão, mesmo `tipo_instituicao` no mesmo `ano`) — sinaliza instituição
    atípica frente aos seus pares no período, independente do seu próprio
    histórico. Usado apenas no Conjunto B (por instituição)."""
    df = df.copy()
    g = df.groupby(list(chave_grupo))[coluna_valor]
    df["zscore_pago_entre_pares"] = (df[coluna_valor] - g.transform("mean")) / g.transform("std").replace(0, pd.NA)
    df["flag_atipico_entre_pares"] = df["zscore_pago_entre_pares"].abs() > 3
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


# --------------------------------------------------------------------------- #
# Tarefa 1.3 — ano parcial, séries curtas e deduplicação por grafia
# --------------------------------------------------------------------------- #
def marcar_series_curtas(df: pd.DataFrame, chave: str, min_anos: int = 5) -> pd.DataFrame:
    """Marca `serie_curta=True` nas linhas de séries com menos de `min_anos`
    anos distintos de observação — z-score e variação anual são pouco
    confiáveis com poucos pontos (ver relatorios/01_qualidade.md, seção 3)."""
    df = df.copy()
    contagem_anos = df.groupby(chave)["ano"].transform("nunique")
    df["serie_curta"] = contagem_anos < min_anos
    return df


def marcar_ano_parcial(df: pd.DataFrame, ano_parcial: int, coluna_ano: str = "ano") -> pd.DataFrame:
    """Marca `ano_parcial=True` nas linhas do ano em que a coleta foi feita
    (tipicamente incompleto — ver ressalva em CLAUDE.md)."""
    df = df.copy()
    df["ano_parcial"] = df[coluna_ano] == ano_parcial
    return df


def deduplicar_series(
    df: pd.DataFrame,
    chave: list[str],
    colunas_soma: list[str],
    coluna_rotulo_preferencial: str | None = None,
) -> pd.DataFrame:
    """Agrega linhas duplicadas em `chave` somando `colunas_soma` e mantendo
    o restante das colunas do registro mais "completo" do grupo (heurística:
    maior soma do comprimento das colunas de texto identificadoras, o que
    tende a preferir grafias acentuadas/com espaçamento correto sobre
    variantes truncadas da mesma fonte). Ver relatorios/01_qualidade.md,
    seção 4, para o achado que motivou esta função (duplicatas de grafia no
    Conjunto A). Sem efeito (retorna cópia inalterada) se não houver
    duplicatas em `chave`.
    """
    df = df.copy()
    if not df.duplicated(subset=chave, keep=False).any():
        return df

    colunas_texto = [c for c in df.columns if c not in colunas_soma + chave]
    df["_prioridade"] = df[colunas_texto].apply(
        lambda linha: sum(len(str(v)) for v in linha), axis=1
    )
    df = df.sort_values("_prioridade", ascending=False)

    colunas_primeiro = [c for c in df.columns if c not in colunas_soma + chave + ["_prioridade"]]
    agregacao = {c: "sum" for c in colunas_soma} | {c: "first" for c in colunas_primeiro}
    resultado = df.groupby(chave, as_index=False).agg(agregacao)
    del coluna_rotulo_preferencial  # reservado para uso futuro (não usado na heurística atual)
    return resultado


def recalcular_serie_temporal_confiavel(
    df: pd.DataFrame, chave: str, coluna_valor: str = "pago_real"
) -> pd.DataFrame:
    """Recalcula `variacao_pago_aa`/`zscore_pago`/`zscore_robusto_pago` e as
    flags correspondentes usando como base estatística SOMENTE as linhas
    elegíveis (`serie_curta=False` e `ano_parcial=False`). Linhas não
    elegíveis recebem NaN nas métricas e `False` nas flags — não entram no
    cálculo de média/desvio da própria série, nem são avaliadas quanto a
    anomalia. Requer que `df` já tenha as colunas `serie_curta` e
    `ano_parcial` (ver `marcar_series_curtas`/`marcar_ano_parcial`).
    """
    colunas_derivadas = [
        "variacao_pago_aa", "zscore_pago", "zscore_robusto_pago",
        "flag_anomalia_zscore", "flag_anomalia_robusto", "flag_salto_anual",
    ]
    df = df.drop(columns=[c for c in colunas_derivadas if c in df.columns]).copy()

    elegivel_mask = ~df["serie_curta"] & ~df["ano_parcial"]
    elegivel = features_serie_temporal(df[elegivel_mask].copy(), chave=chave, coluna_valor=coluna_valor)

    df = df.merge(elegivel[[chave, "ano"] + colunas_derivadas], on=[chave, "ano"], how="left")
    for col in ("flag_anomalia_zscore", "flag_anomalia_robusto", "flag_salto_anual"):
        df[col] = df[col].fillna(False).astype(bool)
    return df


def recalcular_zscore_entre_pares_confiavel(
    df: pd.DataFrame,
    chave: str = "chave_serie",
    coluna_valor: str = "pago_real",
    chave_grupo: tuple[str, str] = ("ano", "tipo_instituicao"),
) -> pd.DataFrame:
    """Recalcula `zscore_pago_entre_pares`/`flag_atipico_entre_pares`
    (Conjunto B) usando apenas linhas elegíveis (`ano_parcial=False`) tanto
    como referência de grupo quanto como avaliadas. Linhas de ano parcial
    ficam com NaN/False — comparar o total de um ano incompleto contra o
    total de anos completos dos pares não é uma comparação justa. Requer
    que `df` já tenha a coluna `ano_parcial`.
    """
    colunas_derivadas = ["zscore_pago_entre_pares", "flag_atipico_entre_pares"]
    df = df.drop(columns=[c for c in colunas_derivadas if c in df.columns]).copy()

    elegivel_mask = ~df["ano_parcial"]
    elegivel = zscore_entre_pares(df[elegivel_mask].copy(), coluna_valor=coluna_valor, chave_grupo=chave_grupo)

    df = df.merge(elegivel[[chave, "ano"] + colunas_derivadas], on=[chave, "ano"], how="left")
    df["flag_atipico_entre_pares"] = df["flag_atipico_entre_pares"].fillna(False).astype(bool)
    return df
