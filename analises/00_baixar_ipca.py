#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pré-requisito da tarefa 1.2 do ROADMAP — obtenção do IPCA anual.

Baixa a série mensal do IPCA (variação % mensal) do SGS/Banco Central do
Brasil — série 433 — e calcula o IPCA acumulado por ano civil (Jan–Dez),
salvando em `dados/externos/ipca_anual.csv` no formato exigido por
EXTERNAL.md (item E1): colunas `ano,ipca_acumulado_pct`.

Esta é a alternativa de automação prevista no próprio EXTERNAL.md ("pode
ser automatizada; se for, documentar"): a API do BCB é pública, não exige
cadastro/chave e não tem relação com a API do Portal da Transparência
(GOVBR_API_KEY não é usada aqui).

Também salva `dados/externos/ipca_anual_detalhe.csv`, com colunas extras
(`n_meses`, `ano_completo`) usadas por `sucuri.deflacao` para identificar o
último ano com os 12 meses disponíveis (o ano corrente da coleta é sempre
parcial — ver ressalva em CLAUDE.md).

Uso:
    uv run python analises/00_baixar_ipca.py
    uv run python analises/00_baixar_ipca.py --ano-inicio 2014
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                     datefmt="%H:%M:%S")
log = logging.getLogger("baixar_ipca")

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
DIR_EXTERNOS = Path("dados/externos")


def baixar_ipca_mensal(ano_inicio: int) -> pd.DataFrame:
    params = {"formato": "json", "dataInicial": f"01/01/{ano_inicio}"}
    resp = requests.get(SGS_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = df["valor"].astype(float)
    df["ano"] = df["data"].dt.year
    return df


def calcular_acumulado_anual(df_mensal: pd.DataFrame) -> pd.DataFrame:
    """IPCA acumulado no ano = produtório de (1 + variação mensal/100) - 1."""
    g = df_mensal.groupby("ano").agg(
        n_meses=("valor", "size"),
        fator_acumulado=("valor", lambda s: (1 + s / 100).prod()),
    )
    g["ipca_acumulado_pct"] = ((g["fator_acumulado"] - 1) * 100).round(4)
    g["ano_completo"] = g["n_meses"] == 12
    return g.drop(columns="fator_acumulado").reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ano-inicio", type=int, default=2014)
    args = parser.parse_args()

    log.info("Baixando IPCA mensal (SGS 433) a partir de %s...", args.ano_inicio)
    df_mensal = baixar_ipca_mensal(args.ano_inicio)
    df_anual = calcular_acumulado_anual(df_mensal)

    DIR_EXTERNOS.mkdir(parents=True, exist_ok=True)
    df_anual[["ano", "ipca_acumulado_pct"]].to_csv(DIR_EXTERNOS / "ipca_anual.csv", index=False)
    df_anual.to_csv(DIR_EXTERNOS / "ipca_anual_detalhe.csv", index=False)

    log.info("Salvo: %s", DIR_EXTERNOS / "ipca_anual.csv")
    log.info("Salvo: %s", DIR_EXTERNOS / "ipca_anual_detalhe.csv")
    print(df_anual.to_string(index=False))


if __name__ == "__main__":
    main()
