#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 1.2 do ROADMAP — Deflacionamento pelo IPCA.

Adiciona `empenhado_real`, `liquidado_real`, `pago_real` (R$ do último ano
completo) aos dois conjuntos e regrava como `dados/*_real.{csv,parquet}`.
Pré-requisito: `dados/externos/ipca_anual.csv` (gerado por
`analises/00_baixar_ipca.py`).

Uso:
    uv run python analises/01b_deflacionar.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from sucuri.deflacao import carregar_ipca, construir_indice_encadeado, deflacionar

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                     datefmt="%H:%M:%S")
log = logging.getLogger("deflacionar")

DIR_DADOS = Path("dados")
COLUNAS_MONETARIAS = ["empenhado", "liquidado", "pago"]


def ultimo_ano_completo(caminho_detalhe: Path) -> int:
    detalhe = pd.read_csv(caminho_detalhe)
    completos = detalhe.loc[detalhe["ano_completo"], "ano"]
    if completos.empty:
        raise ValueError(f"Nenhum ano completo encontrado em {caminho_detalhe}.")
    return int(completos.max())


def processar(nome_base: str, ano_base: int, indice: pd.Series) -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / f"{nome_base}.parquet")
    df_real = deflacionar(df, indice, ano_base, COLUNAS_MONETARIAS)

    caminho_csv = DIR_DADOS / f"{nome_base}_real.csv"
    caminho_pq = DIR_DADOS / f"{nome_base}_real.parquet"
    df_real.to_csv(caminho_csv, index=False, encoding="utf-8")
    df_real.to_parquet(caminho_pq, index=False)
    log.info("[%s] salvo: %s, %s (ano-base %s)", nome_base, caminho_csv, caminho_pq, ano_base)
    return df_real


def main() -> None:
    ipca_df = carregar_ipca()
    ano_base = ultimo_ano_completo(Path("dados/externos/ipca_anual_detalhe.csv"))
    indice = construir_indice_encadeado(ipca_df)
    log.info("Ano-base (último ano completo de IPCA): %s", ano_base)

    for nome in ("despesas_ensino_superior", "despesas_por_instituicao"):
        df_real = processar(nome, ano_base, indice)
        # Checagem de sanidade: valores de 2014 corrigidos devem ficar
        # maiores que os nominais (mais inflação acumulada até o ano-base).
        linhas_2014 = df_real[df_real["ano"] == 2014]
        if not linhas_2014.empty:
            nominal = linhas_2014["pago"].sum()
            real = linhas_2014["pago_real"].sum()
            log.info("[%s] 2014: pago nominal=%.0f | pago_real (%s)=%.0f | fator=%.3f",
                      nome, nominal, ano_base, real, real / nominal if nominal else float("nan"))

    log.info("Concluído.")


if __name__ == "__main__":
    main()
