"""Coletor de licitações — tarefa 3.3 do ROADMAP.

Endpoint `/licitacoes`: filtra por `codigoOrgao`, mas **o período aceito é
de no máximo 1 mês por requisição** (achado empírico — a API rejeita
intervalos maiores com HTTP 400 "O período deve ser de no máximo 1 mês.",
diferente de `/contratos`, que aceita anos inteiros). Cobrir um ano de uma
instituição custa 12 requisições (bem mais barato que os 365×3 de
`/despesas/documentos` na tarefa 3.1, mas ainda uma restrição real de
desenho a respeitar ao planejar coletas maiores).
"""

from __future__ import annotations

import calendar
from datetime import date

import pandas as pd

from sucuri.api import ENDPOINT_LICITACOES, coletar_paginado

TERMOS_DESERTA_FRACASSADA = ("DESERTA", "FRACASSAD")


def _meses_no_intervalo(data_inicio: date, data_fim: date) -> list[tuple[int, int]]:
    """Lista de (ano, mês) cobrindo o intervalo, inclusive nas pontas."""
    meses = []
    ano, mes = data_inicio.year, data_inicio.month
    while (ano, mes) <= (data_fim.year, data_fim.month):
        meses.append((ano, mes))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return meses


def coletar_licitacoes_periodo(sessao, codigo_orgao: str, data_inicio: date, data_fim: date) -> list[dict]:
    """Coleta licitações de um órgão mês a mês (limite da API) entre
    `data_inicio` e `data_fim`."""
    registros: list[dict] = []
    for ano, mes in _meses_no_intervalo(data_inicio, data_fim):
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        params = {
            "codigoOrgao": codigo_orgao,
            "dataInicial": f"01/{mes:02d}/{ano}",
            "dataFinal": f"{ultimo_dia:02d}/{mes:02d}/{ano}",
        }
        registros.extend(coletar_paginado(
            sessao, ENDPOINT_LICITACOES, params, f"licitacoes orgao={codigo_orgao} {mes:02d}/{ano}"
        ))
    return registros


def construir_df_licitacoes(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        licitacao = r.get("licitacao") or {}
        ug = r.get("unidadeGestora") or {}
        orgao_vinculado = ug.get("orgaoVinculado") or {}
        situacao = r.get("situacaoCompra") or ""
        linhas.append({
            "id": r.get("id"),
            "numero": licitacao.get("numero"),
            "numeroProcesso": licitacao.get("numeroProcesso"),
            "objeto": licitacao.get("objeto"),
            "codigoOrgao": orgao_vinculado.get("codigoSIAFI"),
            "orgao": orgao_vinculado.get("nome"),
            "modalidadeLicitacao": r.get("modalidadeLicitacao"),
            "situacaoCompra": situacao,
            "eh_deserta_ou_fracassada": any(t in situacao.upper() for t in TERMOS_DESERTA_FRACASSADA),
            "dataAbertura": r.get("dataAbertura"),
            "dataResultadoCompra": r.get("dataResultadoCompra"),
            "valor": r.get("valor") or 0.0,
        })
    df = pd.DataFrame(linhas)
    df["dataAbertura"] = pd.to_datetime(df["dataAbertura"], errors="coerce")
    df["ano"] = df["dataAbertura"].dt.year
    return df


def desertas_repetidas(df: pd.DataFrame, min_ocorrencias: int = 2) -> pd.DataFrame:
    """Órgãos×ano com `min_ocorrencias` ou mais licitações desertas/fracassadas."""
    if df.empty:
        return pd.DataFrame(columns=["codigoOrgao", "orgao", "ano", "n_desertas_fracassadas"])
    contagem = (
        df[df["eh_deserta_ou_fracassada"]]
        .groupby(["codigoOrgao", "orgao", "ano"])
        .size()
        .reset_index(name="n_desertas_fracassadas")
    )
    return contagem[contagem["n_desertas_fracassadas"] >= min_ocorrencias].sort_values(
        "n_desertas_fracassadas", ascending=False
    )
