"""Baixa a população residente estimada do IBGE (Brasil e por UF) para
cruzamento com os dados do Portal da Transparência.

Fonte: API de agregados do IBGE (servicodados), agregado 6579, variável 9324
— pública, sem chave, sem relação com `GOVBR_API_KEY`. Ver `sucuri.ibge`.

Saídas (dados/externos/, mesmo padrão do IPCA em 00_baixar_ipca.py):
- ibge_populacao_brasil.csv  (ano, populacao, interpolado)
- ibge_populacao_uf.csv      (ano, sigla_uf, uf, populacao, interpolado)

A série de estimativas tem lacunas nos anos de Censo (2022) e em anos sem
estimativa publicada (ex.: 2023): esses anos são preenchidos por interpolação
linear entre os vizinhos e marcados com `interpolado=True` — toda análise
que os use deve carregar essa ressalva.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sucuri.ibge import (
    AGREGADO_POPULACAO,
    NIVEL_BRASIL,
    NIVEL_UF,
    SIGLA_POR_NOME_UF,
    VARIAVEL_POPULACAO,
    consultar_agregado,
    extrair_series,
    interpolar_anos_faltantes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("baixar_ibge")

ANO_INICIO = 2014
ANO_FIM = 2025
DIR_SAIDA = Path("dados/externos")


def main() -> None:
    anos = list(range(ANO_INICIO, ANO_FIM + 1))
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    for nivel, nome_arquivo in [
        (NIVEL_BRASIL, "ibge_populacao_brasil.csv"),
        (NIVEL_UF, "ibge_populacao_uf.csv"),
    ]:
        log.info("Consultando agregado %s (%s) para %s–%s ...",
                 AGREGADO_POPULACAO, nivel, ANO_INICIO, ANO_FIM)
        payload = consultar_agregado(AGREGADO_POPULACAO, VARIAVEL_POPULACAO, anos, nivel=nivel)
        df = extrair_series(payload)
        anos_obtidos = sorted(df["ano"].unique())
        faltantes = sorted(set(anos) - set(anos_obtidos))
        if faltantes:
            log.info("Anos sem estimativa publicada %s — interpolação linear "
                     "(marcada em 'interpolado').", faltantes)
        df = interpolar_anos_faltantes(df, anos)
        df = df.rename(columns={"valor": "populacao", "localidade": "uf"})

        if nivel == NIVEL_UF:
            df["sigla_uf"] = df["uf"].str.upper().map(SIGLA_POR_NOME_UF)
            df = df[["ano", "sigla_uf", "uf", "populacao", "interpolado"]]
        else:
            df = df[["ano", "populacao", "interpolado"]]

        df = df.sort_values(["ano"] + (["sigla_uf"] if nivel == NIVEL_UF else [])).reset_index(drop=True)
        caminho = DIR_SAIDA / nome_arquivo
        df.to_csv(caminho, index=False)
        log.info("Salvo %s (%d linhas, %d interpoladas).",
                 caminho, len(df), int(df["interpolado"].sum()))


if __name__ == "__main__":
    main()
