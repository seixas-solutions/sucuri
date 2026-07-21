"""Baixa dados do IBGE via sidrapy (API SIDRA) para cruzamento com os dados
do Portal da Transparência.

Fonte: API SIDRA do IBGE via biblioteca `sidrapy` — pública, sem chave, sem
relação com `GOVBR_API_KEY`. Ver `sucuri.ibge`.

Saídas (dados/externos/, mesmo padrão do IPCA em 00_baixar_ipca.py):
- ibge_populacao_brasil.csv  (ano, populacao, interpolado)        [tabela 6579]
- ibge_populacao_uf.csv      (ano, sigla_uf, uf, populacao, interpolado)
- ibge_pib_uf.csv            (ano, sigla_uf, uf, pib_mil_reais)   [tabela 5938]

Ressalvas estruturais das fontes (propagadas às análises):
- População: anos de Censo/transição (2022, 2023) não têm estimativa
  publicada na tabela 6579 — preenchidos por interpolação linear entre os
  vizinhos e marcados com `interpolado=True`.
- PIB (Contas Regionais): publicado com defasagem de ~2 anos — a série vai
  só até o último ano disponível (hoje 2022), sem interpolação (não faz
  sentido interpolar o fim da série).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from sucuri.ibge import (
    NIVEL_BRASIL,
    NIVEL_UF,
    SIGLA_POR_NOME_UF,
    TABELA_PIB_UF,
    TABELA_POPULACAO,
    VARIAVEL_PIB,
    VARIAVEL_POPULACAO,
    coletar_tabela_sidra,
    interpolar_anos_faltantes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("baixar_ibge")

ANO_INICIO = 2014
ANO_FIM = 2025
DIR_SAIDA = Path("dados/externos")


def adicionar_sigla_uf(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"localidade": "uf"})
    df["sigla_uf"] = df["uf"].str.upper().map(SIGLA_POR_NOME_UF)
    return df


def baixar_populacao() -> None:
    anos = list(range(ANO_INICIO, ANO_FIM + 1))
    periodo = f"{ANO_INICIO}-{ANO_FIM}"

    for nivel, nome_arquivo in [
        (NIVEL_BRASIL, "ibge_populacao_brasil.csv"),
        (NIVEL_UF, "ibge_populacao_uf.csv"),
    ]:
        log.info("SIDRA tabela %s (população, nível %s), %s ...",
                 TABELA_POPULACAO, nivel, periodo)
        df = coletar_tabela_sidra(TABELA_POPULACAO, VARIAVEL_POPULACAO, periodo, nivel=nivel)
        faltantes = sorted(set(anos) - set(df["ano"].unique()))
        if faltantes:
            log.info("Anos sem estimativa publicada %s — interpolação linear "
                     "(marcada em 'interpolado').", faltantes)
        df = interpolar_anos_faltantes(df, anos).rename(columns={"valor": "populacao"})

        if nivel == NIVEL_UF:
            df = adicionar_sigla_uf(df)
            df = df[["ano", "sigla_uf", "uf", "populacao", "interpolado"]]
            df = df.sort_values(["ano", "sigla_uf"])
        else:
            df = df[["ano", "populacao", "interpolado"]].sort_values("ano")

        caminho = DIR_SAIDA / nome_arquivo
        df.reset_index(drop=True).to_csv(caminho, index=False)
        log.info("Salvo %s (%d linhas, %d interpoladas).",
                 caminho, len(df), int(df["interpolado"].sum()))


def baixar_pib_uf() -> None:
    periodo = f"{ANO_INICIO}-{ANO_FIM}"
    log.info("SIDRA tabela %s (PIB por UF, preços correntes), %s ...", TABELA_PIB_UF, periodo)
    df = coletar_tabela_sidra(TABELA_PIB_UF, VARIAVEL_PIB, periodo, nivel=NIVEL_UF)
    df = adicionar_sigla_uf(df).rename(columns={"valor": "pib_mil_reais"})
    df = df[["ano", "sigla_uf", "uf", "pib_mil_reais"]].sort_values(["ano", "sigla_uf"])
    caminho = DIR_SAIDA / "ibge_pib_uf.csv"
    df.reset_index(drop=True).to_csv(caminho, index=False)
    log.info("Salvo %s (%d linhas, %d–%d — Contas Regionais têm defasagem de ~2 anos).",
             caminho, len(df), int(df["ano"].min()), int(df["ano"].max()))


def main() -> None:
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    baixar_populacao()
    baixar_pib_uf()


if __name__ == "__main__":
    main()
