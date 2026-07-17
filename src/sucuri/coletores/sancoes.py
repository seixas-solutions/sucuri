"""Coletor de sanções (CEIS, CNEP, acordos de leniência) — tarefa 3.4 do ROADMAP.

Os três endpoints (`/ceis`, `/cnep`, `/acordos-leniencia`) filtram por
CNPJ/CPF do sancionado, não por órgão — e são registros nacionais grandes
(o CEIS sozinho tem mais de 12 mil páginas de 15 registros, confirmado
empiricamente; baixar tudo é impraticável para um piloto). A estratégia
aqui é o oposto de "baixar tudo e cruzar depois": consulta **direcionada**,
um CNPJ de fornecedor por vez, usando os fornecedores já coletados em
`dados/contratos_mec.parquet` (tarefa 3.2) como lista de entrada.
"""

from __future__ import annotations

import time

import pandas as pd

from sucuri.api import (
    ENDPOINT_ACORDOS_LENIENCIA,
    ENDPOINT_CEIS,
    ENDPOINT_CNEP,
    PAUSA_ENTRE_REQUISICOES_S,
    requisitar,
)


def consultar_sancoes_cnpj(sessao, cnpj: str) -> dict[str, list[dict]]:
    """Consulta os três registros de sanção para um único CNPJ/CPF.
    3 requisições por chamada (CEIS + CNEP + acordos de leniência)."""
    ceis = requisitar(sessao, ENDPOINT_CEIS, {"codigoSancionado": cnpj, "pagina": 1})
    time.sleep(PAUSA_ENTRE_REQUISICOES_S)
    cnep = requisitar(sessao, ENDPOINT_CNEP, {"codigoSancionado": cnpj, "pagina": 1})
    time.sleep(PAUSA_ENTRE_REQUISICOES_S)
    leniencia = requisitar(sessao, ENDPOINT_ACORDOS_LENIENCIA, {"cnpjSancionado": cnpj, "pagina": 1})
    time.sleep(PAUSA_ENTRE_REQUISICOES_S)
    return {"ceis": ceis, "cnep": cnep, "acordos_leniencia": leniencia}


def consultar_sancoes_lista_cnpjs(sessao, cnpjs: list[str]) -> list[dict]:
    """Consulta sanções para uma lista de CNPJs/CPFs, retornando uma lista
    plana de registros de sanção (cada um com a fonte e o CNPJ consultado
    anexados). CNPJs sem nenhuma sanção não geram registro (lista pode ser
    menor que 3×len(cnpjs))."""
    registros: list[dict] = []
    for cnpj in cnpjs:
        resultado = consultar_sancoes_cnpj(sessao, cnpj)
        for fonte, itens in resultado.items():
            for item in itens:
                item["_fonte"] = fonte
                item["_cnpj_consultado"] = cnpj
                registros.append(item)
    return registros


def construir_df_sancoes(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        sancionado = r.get("sancionado") or {}
        orgao_sancionador = r.get("orgaoSancionador") or {}
        tipo_sancao = r.get("tipoSancao") or {}
        linhas.append({
            "fonte": r.get("_fonte"),
            "cnpjConsultado": r.get("_cnpj_consultado"),
            "cnpjSancionado": sancionado.get("codigoFormatado"),
            "nomeSancionado": sancionado.get("nome"),
            "orgaoSancionador": orgao_sancionador.get("nomeExibicao") or r.get("orgaoSancionador"),
            "tipoSancao": tipo_sancao.get("descricaoResumida") if isinstance(tipo_sancao, dict) else tipo_sancao,
            "dataInicioSancao": r.get("dataInicioSancao"),
            "dataFimSancao": r.get("dataFimSancao"),
        })
    df = pd.DataFrame(linhas)
    df["dataInicioSancao"] = pd.to_datetime(df["dataInicioSancao"], format="%d/%m/%Y", errors="coerce")
    df["dataFimSancao"] = pd.to_datetime(df["dataFimSancao"], format="%d/%m/%Y", errors="coerce")
    return df


def cruzar_contratos_sancionados(df_contratos: pd.DataFrame, df_sancoes: pd.DataFrame) -> pd.DataFrame:
    """Contratos cujo fornecedor já estava sancionado NA DATA DA ASSINATURA
    do contrato (sinal forte, per ROADMAP) — não apenas "fornecedor tem
    alguma sanção em algum momento", que seria um falso positivo comum
    (sanção aplicada depois do contrato assinado não é a mesma coisa).
    """
    if df_contratos.empty or df_sancoes.empty:
        return pd.DataFrame()

    cruzado = df_contratos.merge(
        df_sancoes, left_on="fornecedorCnpjCpf", right_on="cnpjSancionado", how="inner"
    )
    if cruzado.empty:
        return cruzado

    sancionado_na_assinatura = (
        (cruzado["dataAssinatura"] >= cruzado["dataInicioSancao"])
        & (cruzado["dataFimSancao"].isna() | (cruzado["dataAssinatura"] <= cruzado["dataFimSancao"]))
    )
    return cruzado[sancionado_na_assinatura]
