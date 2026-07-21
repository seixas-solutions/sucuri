"""Painel interativo local (tarefa 5.2 do ROADMAP) — Flask.

Visualiza os produtos das Fases 1–4 sem recalcular nenhuma estatística nova:
séries por instituição (Conjunto B `_v2`), medidas de anomalia (z-scores,
scores IF/LOF, eventos de tendência Theil–Sen, casos priorizados),
contratos/fornecedores (tarefa 3.2) e cruzamentos IBGE (tarefa 4.4).
Somente leitura dos arquivos de `dados/`; gráficos renderizados no servidor
com matplotlib (paleta do projeto, `sucuri.graficos`) e embutidos como PNG
base64 — sem dependência de CDN/JavaScript externo.

Uso:
    uv run --group painel flask --app painel/app.py run
    # ou: uv run --group painel python painel/app.py
"""

from __future__ import annotations

import base64
import io
import threading
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from flask import Flask, abort, render_template, request  # noqa: E402

from sucuri.coletores.contratos import indice_herfindahl  # noqa: E402
from sucuri.utils import sigla_instituicao  # noqa: E402
from sucuri.graficos import (  # noqa: E402
    COR_DIVERGENTE_NEG,
    COR_SEQUENCIAL,
    PALETA_CATEGORICA,
    aplicar_estilo,
)

DIR_DADOS = Path(__file__).resolve().parent.parent / "dados"

AVISO_METODOLOGICO = (
    "Atipicidade estatística ≠ irregularidade. Todos os sinais deste painel são "
    "indícios a investigar, nunca confirmação de desvio. Valores comparados entre "
    "anos estão em R$ de 2025 (IPCA) quando indicado; o ano parcial da coleta fica "
    "fora das estatísticas por construção."
)

app = Flask(__name__)
_trava_matplotlib = threading.Lock()


@lru_cache(maxsize=None)
def carregar(nome: str) -> pd.DataFrame:
    caminho = DIR_DADOS / nome
    if not caminho.exists():
        return pd.DataFrame()
    if caminho.suffix == ".parquet":
        return pd.read_parquet(caminho)
    return pd.read_csv(caminho)


def fig_para_base64(fig: plt.Figure) -> str:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# --------------------------------------------------------------------- gráficos
def grafico_evolucao_anual() -> str:
    df_a = carregar("despesas_ensino_superior_v2.parquet")
    df_b = carregar("despesas_por_instituicao_v2.parquet")
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 4))
        for df, rotulo, cor in [
            (df_b, "Conjunto B — órgãos do MEC (todas as funções)", PALETA_CATEGORICA[0]),
            (df_a, "Conjunto A — subfunção 364 (Ensino Superior)", PALETA_CATEGORICA[1]),
        ]:
            serie = df[~df["ano_parcial"]].groupby("ano")["pago_real"].sum() / 1e9
            ax.plot(serie.index, serie.values, marker="o", label=rotulo, color=cor)
        ax.set_xlabel("Ano")
        ax.set_ylabel("Pago (R$ bilhões de 2025)")
        ax.legend(loc="center right", fontsize=8)
        return fig_para_base64(fig)


def grafico_serie_instituicao(orgao: str) -> str:
    df = carregar("despesas_por_instituicao_v2.parquet")
    serie = df[df["orgao"] == orgao].sort_values("ano")
    eventos = carregar("eventos_series.csv")
    eventos_orgao = eventos[eventos["orgao"] == orgao]
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(serie["ano"], serie["pago_real"] / 1e6, marker="o",
                color=COR_SEQUENCIAL, label="pago_real")
        flags = serie[serie["flag_anomalia"].fillna(False)]
        if not flags.empty:
            ax.scatter(flags["ano"], flags["pago_real"] / 1e6, s=110, zorder=3,
                       color=COR_DIVERGENTE_NEG, label="flag de anomalia")
        if not eventos_orgao.empty:
            ax.scatter(eventos_orgao["ano"], eventos_orgao["pago_real"] / 1e6, s=180,
                       zorder=2, facecolors="none", edgecolors=PALETA_CATEGORICA[6],
                       linewidths=2, label="evento Theil–Sen (2.4)")
        parcial = serie[serie["ano_parcial"]]
        if not parcial.empty:
            ax.scatter(parcial["ano"], parcial["pago_real"] / 1e6, marker="s", s=60,
                       color=PALETA_CATEGORICA[3], label="ano parcial (fora das estatísticas)")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Pago (R$ milhões de 2025)")
        ax.set_title(sigla_instituicao(orgao), fontsize=10)
        ax.legend(fontsize=8)
        return fig_para_base64(fig)


def grafico_zscores_instituicao(orgao: str) -> str:
    df = carregar("despesas_por_instituicao_v2.parquet")
    serie = df[df["orgao"] == orgao].sort_values("ano")
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 3.2))
        largura = 0.4
        ax.bar(serie["ano"] - largura / 2, serie["zscore_robusto_pago"], largura,
               color=PALETA_CATEGORICA[0], label="z robusto (série própria)")
        ax.bar(serie["ano"] + largura / 2, serie["zscore_pago_entre_pares"], largura,
               color=PALETA_CATEGORICA[5], label="z entre pares (mesmo tipo)")
        for limiar, estilo in [(3.5, "--"), (-3.5, "--"), (3.0, ":"), (-3.0, ":")]:
            ax.axhline(limiar, color=COR_DIVERGENTE_NEG, linestyle=estilo, linewidth=0.8)
        ax.set_xlabel("Ano")
        ax.set_ylabel("z-score")
        ax.legend(fontsize=8)
        return fig_para_base64(fig)


def grafico_mapa_flags(tipo: str) -> str:
    df = carregar("despesas_por_instituicao_v2.parquet")
    recorte = df[df["tipo_instituicao"] == tipo]
    mapa = (
        recorte.assign(flag=recorte["flag_anomalia"].fillna(False).astype(int))
        .pivot_table(index="orgao", columns="ano", values="flag", aggfunc="max")
    )
    mapa = mapa.loc[mapa.sum(axis=1).sort_values(ascending=True).index]
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, max(3.0, 0.28 * len(mapa))))
        ax.imshow(mapa.values, aspect="auto", cmap="Reds", vmin=0, vmax=1)
        ax.set_xticks(range(len(mapa.columns)), [str(int(a)) for a in mapa.columns],
                      fontsize=7, rotation=45)
        ax.set_yticks(range(len(mapa.index)),
                      [sigla_instituicao(nome) for nome in mapa.index], fontsize=7)
        ax.grid(False)
        ax.set_title(f"flag_anomalia por instituição × ano — {tipo}", fontsize=9)
        return fig_para_base64(fig)


def grafico_distribuicao_scores() -> str:
    scores = carregar("despesas_por_instituicao_scores.parquet")
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 3.2))
        valores = scores["score_anomalia"].dropna()
        corte = valores.quantile(0.9)
        ax.hist(valores, bins=40, color=COR_SEQUENCIAL)
        ax.axvline(corte, color=COR_DIVERGENTE_NEG, linestyle="--",
                   label=f"top 10% (corte da tarefa 2.5): {corte:.2f}")
        ax.set_xlabel("score_anomalia (média IF + LOF normalizados, tarefa 2.3)")
        ax.set_ylabel("nº de linhas")
        ax.legend(fontsize=8)
        return fig_para_base64(fig)


def grafico_top_fornecedores(orgao: str) -> str:
    df = carregar("contratos_mec.parquet")
    recorte = df[df["orgao"] == orgao]
    top = (
        recorte.groupby("fornecedorNome")["valorFinalCompra"].sum()
        .sort_values(ascending=True).tail(12) / 1e6
    )
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.barh([nome[:55] for nome in top.index], top.values, color=COR_SEQUENCIAL)
        ax.set_xlabel("Valor contratado 2023–2025 (R$ milhões, nominal)")
        ax.set_title(sigla_instituicao(orgao), fontsize=10)
        ax.tick_params(axis="y", labelsize=7)
        return fig_para_base64(fig)


def grafico_ibge(nome_csv: str, coluna: str, rotulo_x: str) -> str:
    df = carregar(nome_csv)
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(7.5, 6))
        dados = df.sort_values(coluna)
        cores = [COR_DIVERGENTE_NEG if flag else COR_SEQUENCIAL
                 for flag in dados["flag_atipico"]]
        ax.barh(dados["sigla_uf"], dados[coluna], color=cores)
        ax.set_xlabel(rotulo_x)
        ax.set_title("Vermelho: |z-score robusto| > 3,5", fontsize=9)
        return fig_para_base64(fig)


def grafico_per_capita_nacional() -> str:
    serie = carregar("per_capita_nacional.csv")
    with _trava_matplotlib:
        aplicar_estilo()
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(serie["ano"], serie["per_capita_real"], marker="o", color=COR_SEQUENCIAL)
        interp = serie[serie["interpolado"]]
        ax.plot(interp["ano"], interp["per_capita_real"], linestyle="none", marker="o",
                markerfacecolor="white", markeredgecolor=COR_SEQUENCIAL)
        ax.set_xlabel("Ano")
        ax.set_ylabel("R$ per capita (R$ de 2025)")
        ax.set_title("Pontos vazados: população interpolada (2022–2023)", fontsize=9)
        return fig_para_base64(fig)


# ----------------------------------------------------------------------- rotas
@app.route("/")
def visao_geral():
    casos = carregar("casos_priorizados.csv")
    df_b = carregar("despesas_por_instituicao_v2.parquet")
    df_a = carregar("despesas_ensino_superior_v2.parquet")
    eventos = carregar("eventos_series.csv")
    cartoes = {
        "Casos priorizados (2.5)": len(casos),
        "— com nº máximo de sinais": int((casos["n_sinais"] == casos["n_sinais"].max()).sum()),
        "Flags Conjunto A / B (1.3)": f"{int(df_a['flag_anomalia'].fillna(False).sum())} / "
                                      f"{int(df_b['flag_anomalia'].fillna(False).sum())}",
        "Eventos Theil–Sen (2.4)": len(eventos),
        "Instituições (Conjunto B)": df_b["orgao"].nunique(),
    }
    return render_template(
        "visao_geral.html", aviso=AVISO_METODOLOGICO, cartoes=cartoes,
        grafico=grafico_evolucao_anual(),
        top_casos=casos.head(10).to_dict("records"),
    )


@app.route("/instituicoes")
def instituicoes():
    df = carregar("despesas_por_instituicao_v2.parquet")
    scores = carregar("despesas_por_instituicao_scores.parquet")
    nomes = sorted(df["orgao"].unique())
    orgao = request.args.get("orgao") or nomes[0]
    if orgao not in nomes:
        abort(404)
    serie = df[df["orgao"] == orgao].sort_values("ano")
    scores_orgao = scores[scores["orgao"] == orgao][["ano", "score_anomalia", "rank_anomalia"]]
    tabela = serie.merge(scores_orgao, on="ano", how="left")[
        ["ano", "pago_real", "variacao_pago_aa", "zscore_robusto_pago",
         "zscore_pago_entre_pares", "score_anomalia", "rank_anomalia",
         "flag_anomalia", "ano_parcial"]
    ]
    return render_template(
        "instituicoes.html", aviso=AVISO_METODOLOGICO, nomes=nomes, orgao=orgao,
        grafico_serie=grafico_serie_instituicao(orgao),
        grafico_z=grafico_zscores_instituicao(orgao),
        linhas=tabela.to_dict("records"),
    )


@app.route("/anomalias")
def anomalias():
    df = carregar("despesas_por_instituicao_v2.parquet")
    casos = carregar("casos_priorizados.csv")
    tipos = sorted(df["tipo_instituicao"].unique())
    tipo = request.args.get("tipo") or "Universidade Federal"
    if tipo not in tipos:
        abort(404)
    min_sinais = request.args.get("min_sinais", default=1, type=int)
    filtrado = casos[casos["n_sinais"] >= min_sinais]
    return render_template(
        "anomalias.html", aviso=AVISO_METODOLOGICO, tipos=tipos, tipo=tipo,
        min_sinais=min_sinais, max_sinais=int(casos["n_sinais"].max()),
        grafico_mapa=grafico_mapa_flags(tipo),
        grafico_scores=grafico_distribuicao_scores(),
        casos=filtrado.to_dict("records"), n_casos=len(filtrado),
    )


@app.route("/contratos")
def contratos():
    df = carregar("contratos_mec.parquet")
    nomes = sorted(df["orgao"].unique())
    orgao = request.args.get("orgao") or nomes[0]
    if orgao not in nomes:
        abort(404)
    hhi = (
        indice_herfindahl(df)
        .merge(df[["codigoOrgao", "orgao"]].drop_duplicates(), on="codigoOrgao")
        .sort_values("hhi_fornecedores", ascending=False)
    )
    recorte = df[df["orgao"] == orgao]
    resumo = {
        "n_contratos": len(recorte),
        "pct_dispensa": 100 * recorte["eh_dispensa_ou_inexigibilidade"].mean(),
        "hhi": float(hhi.loc[hhi["orgao"] == orgao, "hhi_fornecedores"].iloc[0]),
    }
    return render_template(
        "contratos.html", aviso=AVISO_METODOLOGICO, nomes=nomes, orgao=orgao,
        resumo=resumo, grafico=grafico_top_fornecedores(orgao),
        hhi=hhi.to_dict("records"),
    )


@app.route("/ibge")
def ibge():
    per_capita = carregar("per_capita_nacional.csv")
    if per_capita.empty:
        return render_template("faltando.html", aviso=AVISO_METODOLOGICO,
                               comando="uv run python analises/00b_baixar_ibge.py && "
                                       "uv run python analises/14_ibge_cruzamento.py")
    emendas_uf = carregar("emendas_per_capita_uf.csv")
    emendas_pib = carregar("emendas_por_pib_uf.csv")
    return render_template(
        "ibge.html", aviso=AVISO_METODOLOGICO,
        grafico_per_capita=grafico_per_capita_nacional(),
        grafico_uf=grafico_ibge("emendas_per_capita_uf.csv", "per_capita_real",
                                "R$ per capita acumulado 2014–2025 (R$ de 2025)"),
        grafico_pib=grafico_ibge("emendas_por_pib_uf.csv", "emendas_por_milhao_pib",
                                 "R$ de emenda por R$ 1 milhão de PIB (2014–2023)"),
        atipicas_capita=", ".join(emendas_uf.loc[emendas_uf["flag_atipico"], "sigla_uf"]),
        atipicas_pib=", ".join(emendas_pib.loc[emendas_pib["flag_atipico"], "sigla_uf"]),
    )


if __name__ == "__main__":
    app.run(debug=False, port=5000)
