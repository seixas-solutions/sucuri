#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 1.3 do ROADMAP — Tratamento do ano parcial e revisão das flags.

Parte de `dados/*_real.{csv,parquet}` (saída da tarefa 1.2) e produz
`dados/*_v2.{csv,parquet}`:

  1. Deduplica o Conjunto A por grafia (achado da tarefa 1.1, seção 4 de
     `relatorios/01_qualidade.md`) — soma as colunas monetárias de linhas
     que só diferem por acentuação/espaçamento no texto do programa/ação.
  2. Marca `ano_parcial=True` no ano da coleta mais recente (detectado pelo
     carimbo de `dados/raw/`).
  3. Marca `serie_curta=True` nas séries com menos de 5 anos de observação.
  4. Recalcula `variacao_pago_aa`/`zscore_pago`/`zscore_robusto_pago` (e, no
     Conjunto B, `zscore_pago_entre_pares`) com base em `pago_real`
     (deflacionado — não nominal), EXCLUINDO linhas de ano parcial e séries
     curtas da base estatística. Essas linhas recebem NaN/False nessas
     colunas — não são avaliadas quanto a anomalia por falta de uma base de
     comparação confiável.

Uso:
    uv run python analises/01c_ano_parcial_e_flags.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from sucuri.features import (
    consolidar_flags,
    deduplicar_series,
    indicadores_execucao,
    marcar_ano_parcial,
    marcar_series_curtas,
    recalcular_serie_temporal_confiavel,
    recalcular_zscore_entre_pares_confiavel,
)
from sucuri.persistencia import detectar_ano_coleta

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                     datefmt="%H:%M:%S")
log = logging.getLogger("ano_parcial_e_flags")

DIR_DADOS = Path("dados")

COLUNAS_BASE_A = [
    "ano", "codigoFuncao", "funcao", "codigoSubfuncao", "subfuncao",
    "codigoPrograma", "programa", "codigoAcao", "acao", "chave_serie",
]
COLUNAS_BASE_B = [
    "ano", "codigoOrgaoSuperior", "orgaoSuperior",
    "codigoOrgao", "orgao", "tipo_instituicao", "chave_serie",
]
COLUNAS_MONETARIAS = ["empenhado", "liquidado", "pago", "empenhado_real", "liquidado_real", "pago_real"]


def _contar_flags(df: pd.DataFrame) -> dict:
    return {
        col: int(df[col].sum())
        for col in df.columns
        if col.startswith("flag_") and df[col].dtype == bool
    }


def processar(
    nome: str, colunas_base: list[str], ano_coleta: int, *, com_pares: bool
) -> tuple[pd.DataFrame, dict, dict]:
    df_original = pd.read_parquet(DIR_DADOS / f"{nome}_real.parquet")
    # "Antes": flags tal como computadas pelo pipeline original (Fase 0),
    # sobre dados nominais, sem dedup e sem exclusão de ano parcial/série curta.
    flags_antes = _contar_flags(df_original)
    n_linhas_antes = len(df_original)

    df = df_original[colunas_base + COLUNAS_MONETARIAS].copy()
    df = deduplicar_series(df, chave=["ano", "chave_serie"], colunas_soma=COLUNAS_MONETARIAS)
    n_linhas_depois_dedup = len(df)

    df = indicadores_execucao(df)
    df = marcar_series_curtas(df, chave="chave_serie")
    df = marcar_ano_parcial(df, ano_parcial=ano_coleta)
    df = recalcular_serie_temporal_confiavel(df, chave="chave_serie", coluna_valor="pago_real")
    if com_pares:
        df = recalcular_zscore_entre_pares_confiavel(df, chave="chave_serie", coluna_valor="pago_real")
        df = consolidar_flags(df, extra=["flag_atipico_entre_pares"])
    else:
        df = consolidar_flags(df)
    flags_depois = _contar_flags(df)

    log.info("[%s] linhas antes da dedup: %d | depois: %d (%d agregadas)",
              nome, n_linhas_antes, n_linhas_depois_dedup, n_linhas_antes - n_linhas_depois_dedup)
    return df, flags_antes, flags_depois


def salvar(df: pd.DataFrame, nome_base: str) -> None:
    caminho_csv = DIR_DADOS / f"{nome_base}_v2.csv"
    caminho_pq = DIR_DADOS / f"{nome_base}_v2.parquet"
    df.to_csv(caminho_csv, index=False, encoding="utf-8")
    df.to_parquet(caminho_pq, index=False)
    log.info("Salvo: %s, %s", caminho_csv, caminho_pq)


def main() -> None:
    ano_coleta = detectar_ano_coleta()
    log.info("Ano da coleta (tratado como ano_parcial): %s", ano_coleta)

    df_a, flags_antes_a, flags_depois_a = processar(
        "despesas_ensino_superior", COLUNAS_BASE_A, ano_coleta, com_pares=False)
    salvar(df_a, "despesas_ensino_superior")

    df_b, flags_antes_b, flags_depois_b = processar(
        "despesas_por_instituicao", COLUNAS_BASE_B, ano_coleta, com_pares=True)
    salvar(df_b, "despesas_por_instituicao")

    log.info("[A] flags ANTES  (pipeline original, nominal, sem dedup/exclusões): %s", flags_antes_a)
    log.info("[A] flags DEPOIS (dedup + pago_real + exclusão ano parcial/série curta): %s", flags_depois_a)
    log.info("[B] flags ANTES  (pipeline original, nominal, sem exclusões): %s", flags_antes_b)
    log.info("[B] flags DEPOIS (pago_real + exclusão ano parcial): %s", flags_depois_b)

    log.info("Concluído.")


if __name__ == "__main__":
    main()
