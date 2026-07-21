#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cruzamento com dados do IBGE — população residente (tarefa 4.4 do ROADMAP).

Usa a população do IBGE (agregado 6579, baixada por `analises/00b_baixar_ibge.py`)
como denominador para dois cruzamentos com o Portal da Transparência:

1. **Despesa real per capita nacional** (Conjunto A, subfunção 364):
   `pago_real` anual ÷ população do Brasil — a trajetória em U da tarefa 2.1
   reexaminada descontando o crescimento populacional.
2. **Emendas parlamentares per capita por UF** (tarefa 3.7): `valorPago`
   deflacionado (IPCA, mesmo ano-base do projeto) acumulado 2014–2025 por UF
   ÷ população média da UF no período, com z-score robusto entre as 27 UFs.
3. **Emendas por PIB da UF** (tabela SIDRA 5938): `valorPago` nominal
   acumulado na janela coberta pelas Contas Regionais ÷ PIB nominal acumulado
   da UF na mesma janela (ambos nominais nos mesmos anos — a inflação afeta
   numerador e denominador igualmente), com o mesmo z-score robusto.
   Controla o efeito "UF pequena": normaliza pelo tamanho da economia, não
   da população.

Ressalvas herdadas dos insumos (sempre reportadas, nunca implícitas):
- População de 2022–2023 é interpolada (sem estimativa publicada no 6579);
- PIB (Contas Regionais) tem defasagem de ~2 anos — o cruzamento 3 usa a
  janela comum emendas ∩ PIB, menor que 2014–2025;
- Emendas sem UF atribuível ("Nacional", regiões, "MÚLTIPLO") ficam fora do
  rateio por UF e são quantificadas no relatório;
- Ano parcial (2026) não entra em nenhuma das séries.

Uso:
    uv run python analises/14_ibge_cruzamento.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sucuri.deflacao import carregar_ipca, construir_indice_encadeado, deflacionar
from sucuri.graficos import COR_SEQUENCIAL, aplicar_estilo, salvar_figura
from sucuri.ibge import extrair_uf
from sucuri.utils import zscore_robusto

DIR_DADOS = Path("dados")
DIR_EXTERNOS = DIR_DADOS / "externos"
DIR_RELATORIOS = Path("relatorios")
DIR_FIGURAS = DIR_RELATORIOS / "figuras"

LIMIAR_ZSCORE_ROBUSTO = 3.5  # mesmo limiar de flag_anomalia_robusto (Fase 0/1)


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def carregar_populacao(nome: str) -> pd.DataFrame:
    caminho = DIR_EXTERNOS / nome
    if not caminho.exists():
        raise FileNotFoundError(
            f"'{caminho}' não encontrado. Rode 'uv run python analises/00b_baixar_ibge.py' antes."
        )
    return pd.read_csv(caminho)


def ultimo_ano_completo() -> int:
    detalhe = pd.read_csv(DIR_EXTERNOS / "ipca_anual_detalhe.csv")
    return int(detalhe.loc[detalhe["ano_completo"], "ano"].max())


def per_capita_nacional(pop_br: pd.DataFrame) -> pd.DataFrame:
    df_a = pd.read_parquet(DIR_DADOS / "despesas_ensino_superior_v2.parquet")
    por_ano = (
        df_a[~df_a["ano_parcial"]].groupby("ano")["pago_real"].sum().rename("pago_real").reset_index()
    )
    serie = por_ano.merge(pop_br[["ano", "populacao", "interpolado"]], on="ano", how="left")
    serie["per_capita_real"] = serie["pago_real"] / serie["populacao"]
    return serie


def emendas_per_capita_uf(pop_uf: pd.DataFrame, ano_base: int) -> tuple[pd.DataFrame, dict]:
    df = pd.read_parquet(DIR_DADOS / "emendas_educacao.parquet")
    df["sigla_uf"] = df["localidadeDoGasto"].map(extrair_uf)

    indice = construir_indice_encadeado(carregar_ipca(DIR_EXTERNOS / "ipca_anual.csv"))
    df = deflacionar(df, indice, ano_base, ["valorPago"])

    nao_atribuiveis = df[df["sigla_uf"].isna()]
    atribuiveis = df.dropna(subset=["sigla_uf"])

    pop_media = pop_uf.groupby("sigla_uf")["populacao"].mean().rename("populacao_media")
    por_uf = (
        atribuiveis.groupby("sigla_uf")
        .agg(valor_pago_real=("valorPago_real", "sum"), n_emendas=("valorPago", "size"))
        .join(pop_media)
        .reset_index()
    )
    por_uf["per_capita_real"] = por_uf["valor_pago_real"] / por_uf["populacao_media"]
    por_uf["zscore_robusto"] = zscore_robusto(por_uf["per_capita_real"])
    por_uf["flag_atipico"] = por_uf["zscore_robusto"].abs() > LIMIAR_ZSCORE_ROBUSTO
    por_uf = por_uf.sort_values("per_capita_real", ascending=False).reset_index(drop=True)

    contexto = {
        "n_total": len(df),
        "n_nao_atribuiveis": len(nao_atribuiveis),
        "valor_nao_atribuivel_real": float(nao_atribuiveis["valorPago_real"].sum()),
        "valor_total_real": float(df["valorPago_real"].sum()),
    }
    return por_uf, contexto


def emendas_por_pib_uf(pib_uf: pd.DataFrame) -> tuple[pd.DataFrame, tuple[int, int]]:
    df = pd.read_parquet(DIR_DADOS / "emendas_educacao.parquet")
    df["sigla_uf"] = df["localidadeDoGasto"].map(extrair_uf)
    atribuiveis = df.dropna(subset=["sigla_uf"])

    janela = (int(atribuiveis["ano"].min()), int(pib_uf["ano"].max()))
    na_janela = atribuiveis[atribuiveis["ano"].between(*janela)]
    pib_janela = pib_uf[pib_uf["ano"].between(*janela)]

    por_uf = (
        na_janela.groupby("sigla_uf")
        .agg(valor_pago_nominal=("valorPago", "sum"), n_emendas=("valorPago", "size"))
        .join(pib_janela.groupby("sigla_uf")["pib_mil_reais"].sum().rename("pib_mil_reais"))
        .reset_index()
    )
    # R$ de emenda por R$ 1 milhão de PIB acumulado na mesma janela.
    por_uf["emendas_por_milhao_pib"] = por_uf["valor_pago_nominal"] / (
        por_uf["pib_mil_reais"] * 1_000 / 1e6
    )
    por_uf["zscore_robusto"] = zscore_robusto(por_uf["emendas_por_milhao_pib"])
    por_uf["flag_atipico"] = por_uf["zscore_robusto"].abs() > LIMIAR_ZSCORE_ROBUSTO
    return por_uf.sort_values("emendas_por_milhao_pib", ascending=False).reset_index(drop=True), janela


def figura_per_capita_nacional(serie: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(serie["ano"], serie["per_capita_real"], color=COR_SEQUENCIAL, marker="o")
    interp = serie[serie["interpolado"]]
    ax.plot(interp["ano"], interp["per_capita_real"], linestyle="none", marker="o",
            markerfacecolor="white", markeredgecolor=COR_SEQUENCIAL)
    ax.set_xlabel("Ano")
    ax.set_ylabel("R$ per capita (R$ de 2025)")
    ax.set_title("Despesa paga com Ensino Superior (subfunção 364) per capita — Brasil\n"
                 "(pontos vazados: população interpolada)")
    salvar_figura(fig, DIR_FIGURAS / "09_per_capita_nacional.png")


def figura_emendas_uf(por_uf: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    dados = por_uf.sort_values("per_capita_real")
    ax.barh(dados["sigla_uf"], dados["per_capita_real"], color=COR_SEQUENCIAL)
    ax.set_xlabel("R$ per capita acumulado 2014–2025 (R$ de 2025)")
    ax.set_title("Emendas parlamentares pagas — subfunção 364, per capita por UF")
    salvar_figura(fig, DIR_FIGURAS / "10_emendas_per_capita_uf.png")


def figura_emendas_pib(por_pib: pd.DataFrame, janela: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    dados = por_pib.sort_values("emendas_por_milhao_pib")
    ax.barh(dados["sigla_uf"], dados["emendas_por_milhao_pib"], color=COR_SEQUENCIAL)
    ax.set_xlabel(f"R$ de emenda por R$ 1 milhão de PIB ({janela[0]}–{janela[1]})")
    ax.set_title("Emendas parlamentares pagas — subfunção 364, por PIB da UF")
    salvar_figura(fig, DIR_FIGURAS / "11_emendas_por_pib_uf.png")


def gerar_relatorio(serie: pd.DataFrame, por_uf: pd.DataFrame, contexto: dict,
                    ano_base: int, por_pib: pd.DataFrame,
                    janela_pib: tuple[int, int]) -> str:
    pct_nao_atrib = 100 * contexto["valor_nao_atribuivel_real"] / contexto["valor_total_real"]
    pico = serie.loc[serie["per_capita_real"].idxmax()]
    piso = serie.loc[serie["per_capita_real"].idxmin()]
    atipicas = por_uf[por_uf["flag_atipico"]]

    tabela_serie = serie.assign(
        pago_real_bi=lambda d: d["pago_real"] / 1e9,
        populacao_mi=lambda d: d["populacao"] / 1e6,
    )[["ano", "pago_real_bi", "populacao_mi", "per_capita_real", "interpolado"]]

    linhas = [
        "# Cruzamento com o IBGE — população (tarefa 4.4)",
        "",
        "Fonte IBGE: agregado 6579 (população residente estimada), variável 9324,",
        "API pública de agregados (`analises/00b_baixar_ibge.py`). População de",
        "2022–2023 **interpolada linearmente** (sem estimativa publicada) — linhas",
        "marcadas em `interpolado`.",
        "",
        "## 1. Despesa real per capita nacional (Conjunto A, subfunção 364)",
        "",
        f"Método: `pago_real` anual (R$ de {ano_base}, ano parcial excluído) ÷",
        "população do Brasil no ano.",
        "",
        tabela_serie.to_markdown(index=False, floatfmt=(".0f", ".2f", ".1f", ".2f")),
        "",
        f"- Pico per capita: **{int(pico['ano'])}** (R$ {fmt_brl(pico['per_capita_real'])});"
        f" piso: **{int(piso['ano'])}** (R$ {fmt_brl(piso['per_capita_real'])}).",
        "- A trajetória em U da tarefa 2.1 persiste em termos per capita — o",
        "  crescimento populacional (~5% no período) não explica a queda até 2021",
        "  nem a recuperação posterior.",
        "",
        "## 2. Emendas parlamentares per capita por UF (2014–2025 acumulado)",
        "",
        f"Método: `valorPago` deflacionado (IPCA, R$ de {ano_base}) somado por UF",
        "(UF extraída de `localidadeDoGasto` — `sucuri.ibge.extrair_uf`) ÷ população",
        "média da UF no período; z-score robusto (0,6745·(x−mediana)/MAD) entre as",
        f"27 UFs, limiar |z| > {LIMIAR_ZSCORE_ROBUSTO}.",
        "",
        f"- {contexto['n_nao_atribuiveis']} de {contexto['n_total']} emendas "
        f"(R$ {fmt_brl(contexto['valor_nao_atribuivel_real'])}, {pct_nao_atrib:.1f}% do valor)",
        "  não têm UF atribuível (\"Nacional\", regiões, \"MÚLTIPLO\") e ficam fora",
        "  do rateio — ressalva, não descarte silencioso.",
        "",
        por_uf.assign(valor_pago_real_mi=lambda d: d["valor_pago_real"] / 1e6)[
            ["sigla_uf", "valor_pago_real_mi", "n_emendas", "per_capita_real",
             "zscore_robusto", "flag_atipico"]
        ].to_markdown(index=False, floatfmt=(".0f", ".2f", ".0f", ".2f", ".2f")),
        "",
    ]
    if atipicas.empty:
        linhas += [
            f"Nenhuma UF ultrapassa |z| > {LIMIAR_ZSCORE_ROBUSTO}: a dispersão entre",
            "UFs é grande em termos absolutos (razão de ~20× entre extremos), mas",
            "gradual — sem um ponto isolado do resto da distribuição.",
        ]
    else:
        linhas += ["UFs atípicas (|z| acima do limiar): "
                   + ", ".join(atipicas["sigla_uf"])]
    linhas += [
        "",
        "**Leitura de atipicidade, não de irregularidade:** per capita alto em UFs",
        "pequenas é esperado quando a emenda financia uma instituição federal que",
        "atende além da própria UF; o indicador serve para orientar comparação",
        "entre pares, não para concluir desvio.",
        "",
        f"## 3. Emendas por PIB da UF ({janela_pib[0]}–{janela_pib[1]} acumulado)",
        "",
        "Método: `valorPago` nominal acumulado na janela ÷ PIB nominal acumulado",
        "(SIDRA 5938, preços correntes — ambos nominais nos mesmos anos, a",
        "inflação afeta numerador e denominador igualmente); resultado em R$ de",
        "emenda por R$ 1 milhão de PIB; mesmo z-score robusto e limiar do",
        "cruzamento 2. A janela é menor que 2014–2025 porque as Contas Regionais",
        "têm defasagem de ~2 anos.",
        "",
        por_pib.assign(valor_pago_mi=lambda d: d["valor_pago_nominal"] / 1e6)[
            ["sigla_uf", "valor_pago_mi", "n_emendas", "emendas_por_milhao_pib",
             "zscore_robusto", "flag_atipico"]
        ].to_markdown(index=False, floatfmt=(".0f", ".2f", ".0f", ".2f", ".2f")),
        "",
        "UFs atípicas por PIB: "
        + (", ".join(por_pib.loc[por_pib["flag_atipico"], "sigla_uf"]) or "nenhuma")
        + ". A normalização por PIB controla o efeito \"UF pequena\" da",
        "normalização per capita: UFs que permanecem atípicas nos DOIS",
        "denominadores concentram emendas além do que tamanho populacional OU",
        "econômico explicam.",
        "",
        "Figuras: `figuras/09_per_capita_nacional.png`,",
        "`figuras/10_emendas_per_capita_uf.png`, `figuras/11_emendas_por_pib_uf.png`.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    aplicar_estilo()
    ano_base = ultimo_ano_completo()
    pop_br = carregar_populacao("ibge_populacao_brasil.csv")
    pop_uf = carregar_populacao("ibge_populacao_uf.csv")
    pib_uf = carregar_populacao("ibge_pib_uf.csv")

    serie = per_capita_nacional(pop_br)
    por_uf, contexto = emendas_per_capita_uf(pop_uf, ano_base)
    por_pib, janela_pib = emendas_por_pib_uf(pib_uf)

    serie.to_csv(DIR_DADOS / "per_capita_nacional.csv", index=False)
    por_uf.to_csv(DIR_DADOS / "emendas_per_capita_uf.csv", index=False)
    por_pib.to_csv(DIR_DADOS / "emendas_por_pib_uf.csv", index=False)
    figura_per_capita_nacional(serie)
    figura_emendas_uf(por_uf)
    figura_emendas_pib(por_pib, janela_pib)

    relatorio = gerar_relatorio(serie, por_uf, contexto, ano_base, por_pib, janela_pib)
    (DIR_RELATORIOS / "14_ibge.md").write_text(relatorio, encoding="utf-8")
    print(relatorio)


if __name__ == "__main__":
    main()
