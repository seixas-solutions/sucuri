"""Coletor de convênios — tarefa 3.5 do ROADMAP.

Endpoint `/convenios`: filtrar por `codigoOrgao=26000` (Ministério da
Educação, órgão superior) já traz convênios de FNDE, CAPES e demais
órgãos subordinados na mesma consulta (confirmado empiricamente — um
registro retornado tinha `orgao.codigoSIAFI=26298` — FNDE — sob
`orgao.orgaoMaximo.codigo=26000`) — não é preciso iterar por
sub-órgão como em `/contratos`/`/licitacoes`. Aceita intervalo de datas
amplo (testado 2018–2025 numa única consulta paginada), como `/contratos`.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from sucuri.api import ENDPOINT_CONVENIOS, coletar_paginado

CODIGO_ORGAO_SUPERIOR_MEC = "26000"


def coletar_convenios(sessao, data_inicial: date, data_final: date,
                       codigo_orgao: str = CODIGO_ORGAO_SUPERIOR_MEC) -> list[dict]:
    params = {
        "codigoOrgao": codigo_orgao,
        "dataInicial": data_inicial.strftime("%d/%m/%Y"),
        "dataFinal": data_final.strftime("%d/%m/%Y"),
    }
    return coletar_paginado(sessao, ENDPOINT_CONVENIOS, params, f"convenios orgao={codigo_orgao}")


def construir_df_convenios(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        convenente = r.get("convenente") or {}
        orgao = r.get("orgao") or {}
        localidade = r.get("localidadePessoa") or {}
        municipio = r.get("municipioConvenente") or {}
        linhas.append({
            "id": r.get("id"),
            "situacao": r.get("situacao"),
            "convenenteCnpjCpf": convenente.get("cnpjFormatado") or convenente.get("cpfFormatado"),
            "convenenteNome": convenente.get("nome"),
            "convenenteTipo": convenente.get("tipo"),
            "localidadeTipo": localidade.get("descricao"),
            "municipioUf": (municipio.get("uf") or {}).get("sigla"),
            "codigoOrgaoConcedente": orgao.get("codigoSIAFI"),
            "orgaoConcedente": orgao.get("nome"),
            "dataInicioVigencia": r.get("dataInicioVigencia"),
            "dataFinalVigencia": r.get("dataFinalVigencia"),
            "valor": r.get("valor") or 0.0,
            "valorLiberado": r.get("valorLiberado") or 0.0,
            "valorContrapartida": r.get("valorContrapartida") or 0.0,
        })
    df = pd.DataFrame(linhas)
    df["dataInicioVigencia"] = pd.to_datetime(df["dataInicioVigencia"], errors="coerce")
    df["ano"] = df["dataInicioVigencia"].dt.year
    df["eh_inadimplente"] = df["situacao"].str.upper().str.contains("INADIMPLENTE", na=False)
    return df


def convenentes_multiplos_inadimplentes(df: pd.DataFrame, min_inadimplentes: int = 2) -> pd.DataFrame:
    """Convenentes com `min_inadimplentes` ou mais convênios inadimplentes."""
    if df.empty:
        return pd.DataFrame(columns=["convenenteCnpjCpf", "convenenteNome", "n_inadimplentes"])
    contagem = (
        df[df["eh_inadimplente"]]
        .groupby(["convenenteCnpjCpf", "convenenteNome"])
        .size()
        .reset_index(name="n_inadimplentes")
    )
    return contagem[contagem["n_inadimplentes"] >= min_inadimplentes].sort_values(
        "n_inadimplentes", ascending=False
    )


def top_convenentes(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Top N convenentes por valor total recebido, com status de
    prestação de contas resumido (quantos dos seus convênios estão
    inadimplentes)."""
    if df.empty:
        return pd.DataFrame()
    agrupado = (
        df.groupby(["convenenteCnpjCpf", "convenenteNome", "convenenteTipo", "localidadeTipo"])
        .agg(
            valor_total=("valor", "sum"),
            n_convenios=("id", "count"),
            n_inadimplentes=("eh_inadimplente", "sum"),
        )
        .reset_index()
        .sort_values("valor_total", ascending=False)
        .head(n)
    )
    return agrupado
