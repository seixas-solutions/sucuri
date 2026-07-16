#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 2.3 do ROADMAP — Modelos não supervisionados (Isolation Forest + LOF).

Features padronizadas: `pago_real`, `taxa_liquidacao`, `taxa_pagamento`,
`variacao_pago_aa`, `restos_a_pagar_frac` (= restos_a_pagar / empenhado —
razão, não afetada pela deflação, calculada sobre valores nominais do
mesmo ano). Linhas com `ano_parcial=True` ou `serie_curta=True` já têm
`variacao_pago_aa` como NaN (tarefa 1.3) e são naturalmente excluídas.

  - Conjunto A: um único modelo sobre todas as linhas elegíveis.
  - Conjunto B: um modelo por `tipo_instituicao` (escalas muito diferentes
    entre tipos — ver `relatorios/02_eda.md`); grupos com menos de 20
    linhas elegíveis são pulados (amostra insuficiente para LOF/IF).

Salva `dados/*_scores.parquet` (linhas elegíveis + score/rank) e
`relatorios/04_outliers.md` com top 20 por conjunto e concordância entre
métodos (Isolation Forest × LOF) e com as flags da Fase 1.

Uso:
    uv run python analises/04_outliers.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sucuri.outliers import AMOSTRA_MINIMA, aplicar_deteccao, concordancia_top_n, recalcular_ranks_globais
from sucuri.utils import razao_segura

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")

FEATURES = ["pago_real", "taxa_liquidacao", "taxa_pagamento", "variacao_pago_aa", "restos_a_pagar_frac"]


def carregar(nome: str) -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / f"{nome}_v2.parquet")
    df["restos_a_pagar_frac"] = razao_segura(df["restos_a_pagar"], df["empenhado"])
    return df


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def processar_conjunto_a() -> tuple[pd.DataFrame, dict]:
    df = carregar("despesas_ensino_superior")
    resultado = aplicar_deteccao(df, FEATURES, min_amostras=AMOSTRA_MINIMA)
    if resultado is None:
        return df.assign(score_anomalia=pd.NA, rank_anomalia=pd.NA), {"processado": False, "n_total": len(df)}
    # Um único grupo aqui, mas recalcular_ranks_globais é idempotente nesse
    # caso (rank de grupo == rank global) — chamado por consistência com B.
    resultado = recalcular_ranks_globais(resultado)
    return resultado, {"processado": True, "n_total": len(df), "n_elegivel": len(resultado)}


def processar_conjunto_b() -> tuple[pd.DataFrame, dict]:
    df = carregar("despesas_por_instituicao")
    partes = []
    grupos_pulados = []
    for tipo, subset in df.groupby("tipo_instituicao"):
        resultado = aplicar_deteccao(subset, FEATURES, min_amostras=AMOSTRA_MINIMA)
        if resultado is None:
            grupos_pulados.append((tipo, len(subset.dropna(subset=FEATURES))))
            continue
        partes.append(resultado)
    if not partes:
        return df.assign(score_anomalia=pd.NA, rank_anomalia=pd.NA), {
            "processado": False, "n_total": len(df), "grupos_pulados": grupos_pulados}
    # Cada parte tem ranks válidos só dentro do seu tipo_instituicao — o
    # rank global (necessário para "top 20 do conjunto" e para as
    # comparações de concordância) só existe depois de concatenar.
    resultado_final = recalcular_ranks_globais(pd.concat(partes, ignore_index=True))
    return resultado_final, {
        "processado": True, "n_total": len(df), "n_elegivel": len(resultado_final),
        "grupos_pulados": grupos_pulados,
    }


def top_20(df: pd.DataFrame, colunas_id: list[str]) -> pd.DataFrame:
    colunas = colunas_id + ["ano", "pago_real", "score_anomalia", "rank_anomalia",
                             "rank_isolation_forest", "rank_lof"]
    colunas = [c for c in colunas if c in df.columns]
    top = df.sort_values("rank_anomalia").head(20)[colunas].copy()
    top["pago_real_mi"] = (top["pago_real"] / 1e6).round(2)
    return top.drop(columns="pago_real")


def matriz_concordancia_flag(df: pd.DataFrame, top_pct: float = 0.10) -> pd.DataFrame:
    """Cruza flag_anomalia (Fase 1) com pertencer ao top X% de score_anomalia
    (Isolation Forest + LOF combinados)."""
    n = len(df)
    k = max(1, int(round(n * top_pct)))
    top_ids = set(df.nsmallest(k, "rank_anomalia").index)
    df = df.copy()
    df["top_score_anomalia"] = df.index.isin(top_ids)
    tab = pd.crosstab(df["flag_anomalia"], df["top_score_anomalia"])
    tab.index = [f"flag_anomalia={v}" for v in tab.index]
    tab.columns = [f"top_{int(top_pct*100)}pct_score={v}" for v in tab.columns]
    return tab.reset_index().rename(columns={"index": ""})


def gerar_relatorio(res_a: pd.DataFrame, meta_a: dict, res_b: pd.DataFrame, meta_b: dict) -> str:
    conc_a = concordancia_top_n(res_a, "rank_isolation_forest", "rank_lof", top_pct=0.10) if meta_a["processado"] else None
    conc_b = concordancia_top_n(res_b, "rank_isolation_forest", "rank_lof", top_pct=0.10) if meta_b["processado"] else None

    top_a_md = tabela_md(top_20(res_a, ["programa", "acao"])) if meta_a["processado"] else "_Não processado._"
    top_b_md = tabela_md(top_20(res_b, ["orgao", "tipo_instituicao"])) if meta_b["processado"] else "_Não processado._"

    matriz_a_md = tabela_md(matriz_concordancia_flag(res_a)) if meta_a["processado"] else "_Não processado._"
    matriz_b_md = tabela_md(matriz_concordancia_flag(res_b)) if meta_b["processado"] else "_Não processado._"

    grupos_pulados_b = meta_b.get("grupos_pulados", [])
    grupos_pulados_txt = (
        "; ".join(f"{t} (n={n})" for t, n in grupos_pulados_b) if grupos_pulados_b else "nenhum"
    )

    linhas = f"""# Modelos não supervisionados de detecção de outliers — tarefa 2.3

Gerado por `analises/04_outliers.py`. Isolation Forest e Local Outlier
Factor (LOF) sobre features padronizadas: `{"`, `".join(FEATURES)}`.
Score combinado (`score_anomalia`) = média dos ranks normalizados dos dois
métodos (0 a 1, 1 = mais anômalo). `rank_anomalia` = posição no ranking
combinado (1 = mais anômalo).

## 1. Conjunto A

Linhas totais: {meta_a["n_total"]}. Linhas elegíveis (sem NaN nas
features — exclui ano parcial e séries curtas, já tratados na Fase 1):
{meta_a.get("n_elegivel", 0)}.

### Top 20 por `score_anomalia`

{top_a_md}

### Concordância entre métodos (top 10% de cada)

Interseção: {conc_a["intersecao"] if conc_a else "n/d"} de {conc_a["k"] if conc_a else "n/d"}
linhas no top 10% de ambos os métodos (índice de Jaccard:
{f"{conc_a['jaccard']:.2f}" if conc_a else "n/d"}).

### Concordância com `flag_anomalia` (Fase 1)

{matriz_a_md}

## 2. Conjunto B (por tipo de instituição)

Linhas totais: {meta_b["n_total"]}. Linhas elegíveis (agregando todos os
tipos processados): {meta_b.get("n_elegivel", 0)}. Grupos pulados por
amostra insuficiente (<{AMOSTRA_MINIMA} linhas elegíveis): {grupos_pulados_txt}.

### Top 20 por `score_anomalia`

{top_b_md}

### Concordância entre métodos (top 10% de cada)

Interseção: {conc_b["intersecao"] if conc_b else "n/d"} de {conc_b["k"] if conc_b else "n/d"}
linhas no top 10% de ambos os métodos (índice de Jaccard:
{f"{conc_b['jaccard']:.2f}" if conc_b else "n/d"}).

### Concordância com `flag_anomalia` (Fase 1)

{matriz_b_md}

## 3. Interpretação

Isolation Forest e LOF detectam tipos diferentes de desvio (isolamento
global vs. densidade local) — concordância parcial é esperada e não é um
defeito: interseção alta indica outliers "óbvios" (destacados nos dois
critérios); pontos capturados por só um método são candidatos mais sutis,
não devem ser descartados. A concordância com `flag_anomalia` mede se os
dois modelos multivariados redescobrem o que as regras univariadas da
Fase 1 já sinalizavam — sobreposição parcial (não total) é o resultado
esperado, já que os modelos usam informação adicional (nível do gasto,
taxas de execução) que as flags de série temporal isoladas não capturam.

Dois padrões no top 20 do Conjunto B já têm explicação estrutural
identificada nas tarefas anteriores, e não devem ser lidos como achados
novos:

- **Universidades federais recém-criadas** (Cariri, Sul da Bahia, Oeste da
  Bahia — 2015): mesmo padrão de rampa de implantação já discutido em
  `relatorios/02_eda.md`, seção 6 — orçamento do primeiro/segundo ano muito
  diferente do padrão maduro da própria instituição, mas coerente com a
  expansão federal de 2013–2014, não um evento atípico de gasto.
- **UFRJ aparece em 4 dos 20 primeiros lugares** (2015–2017, 2025): dentro
  do grupo `Universidade Federal` (791 linhas, todas as universidades
  federais juntas, sem subdivisão por porte), UFRJ está entre as maiores
  em valor absoluto — o modelo pode estar capturando principalmente
  **dominância de escala** (uma universidade grande destoa de centenas de
  universidades menores no mesmo grupo), não necessariamente comportamento
  atípico de execução orçamentária. Uma iteração futura poderia
  segmentar `Universidade Federal` por porte (matrículas/orçamento) antes
  de rodar os modelos, isolando esse efeito.

Os demais casos do top 20 (institutos federais de porte médio, Hospitalar/
EBSERH, INEP) não têm explicação estrutural evidente nos dados já
analisados e permanecem como prioridade de checagem manual — consolidados
com os demais sinais na tarefa 2.5.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)

    res_a, meta_a = processar_conjunto_a()
    res_b, meta_b = processar_conjunto_b()

    res_a.to_parquet(DIR_DADOS / "despesas_ensino_superior_scores.parquet", index=False)
    res_b.to_parquet(DIR_DADOS / "despesas_por_instituicao_scores.parquet", index=False)

    conteudo = gerar_relatorio(res_a, meta_a, res_b, meta_b)
    caminho = DIR_RELATORIOS / "04_outliers.md"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho}")
    print(f"Salvo: dados/despesas_ensino_superior_scores.parquet ({meta_a})")
    print(f"Salvo: dados/despesas_por_instituicao_scores.parquet ({meta_b})")


if __name__ == "__main__":
    main()
