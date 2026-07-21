"""Painel interativo local (tarefa 5.2 do ROADMAP) — Streamlit.

Visualiza os produtos das Fases 1–4 sem recalcular nada: séries por
instituição (Conjunto B `_v2`), mapa de flags, casos priorizados (tarefa
2.5), drill-down de contratos/fornecedores (tarefa 3.2) e os cruzamentos
com o IBGE (tarefa 4.4). Somente leitura dos arquivos de `dados/`.

Uso:
    uv run --group painel streamlit run painel/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DIR_DADOS = Path(__file__).resolve().parent.parent / "dados"

AVISO_METODOLOGICO = (
    "**Atipicidade estatística ≠ irregularidade.** Todos os sinais deste painel "
    "são indícios a investigar, nunca confirmação de desvio. Valores monetários "
    "em R$ de 2025 (deflacionados pelo IPCA) quando indicado; o ano corrente da "
    "coleta é parcial e fica fora das estatísticas."
)


@st.cache_data
def carregar(nome: str) -> pd.DataFrame:
    caminho = DIR_DADOS / nome
    if not caminho.exists():
        return pd.DataFrame()
    if caminho.suffix == ".parquet":
        return pd.read_parquet(caminho)
    return pd.read_csv(caminho)


def pagina_series() -> None:
    st.header("Séries por instituição (Conjunto B)")
    df = carregar("despesas_por_instituicao_v2.parquet")
    if df.empty:
        st.warning("dados/despesas_por_instituicao_v2.parquet não encontrado.")
        return
    instituicoes = sorted(df["orgao"].unique())
    orgao = st.selectbox("Instituição", instituicoes)
    serie = df[df["orgao"] == orgao].sort_values("ano")

    st.line_chart(serie.set_index("ano")[["pago_real", "empenhado_real"]])
    flags = serie[serie["flag_anomalia"].fillna(False)]
    if not flags.empty:
        st.markdown("**Anos com alguma flag de anomalia:** "
                    + ", ".join(str(int(a)) for a in flags["ano"]))
    st.caption("Total do órgão em todas as funções (não só subfunção 364) — ver CLAUDE.md. "
               "Ano parcial excluído das flags por construção.")
    st.dataframe(
        serie[["ano", "pago", "pago_real", "variacao_pago_aa", "zscore_robusto_pago",
               "flag_anomalia", "ano_parcial"]],
        width="stretch", hide_index=True,
    )


def pagina_mapa_flags() -> None:
    st.header("Mapa de flags por instituição × ano")
    df = carregar("despesas_por_instituicao_v2.parquet")
    if df.empty:
        st.warning("dados/despesas_por_instituicao_v2.parquet não encontrado.")
        return
    tipos = sorted(df["tipo_instituicao"].unique())
    tipo = st.selectbox("Tipo de instituição", tipos)
    recorte = df[df["tipo_instituicao"] == tipo]
    mapa = (
        recorte.assign(flag=recorte["flag_anomalia"].fillna(False).astype(int))
        .pivot_table(index="orgao", columns="ano", values="flag", aggfunc="max")
    )
    mapa = mapa.loc[mapa.sum(axis=1).sort_values(ascending=False).index]
    st.dataframe(
        mapa.style.background_gradient(cmap="Reds", axis=None),
        width="stretch",
    )
    st.caption("1 = alguma flag de anomalia no ano (z-score, salto anual, entre pares...). "
               "Ano parcial nunca gera flag.")


def pagina_casos() -> None:
    st.header("Casos priorizados (tarefa 2.5)")
    df = carregar("casos_priorizados.csv")
    if df.empty:
        st.warning("dados/casos_priorizados.csv não encontrado.")
        return
    col1, col2 = st.columns(2)
    n_sinais_min = col1.slider("Mínimo de sinais concordantes", 1, int(df["n_sinais"].max()), 1)
    anos = col2.multiselect("Anos", sorted(df["ano"].unique()))
    filtrado = df[df["n_sinais"] >= n_sinais_min]
    if anos:
        filtrado = filtrado[filtrado["ano"].isin(anos)]
    st.metric("Casos exibidos", len(filtrado))
    st.dataframe(filtrado, width="stretch", hide_index=True)


def pagina_contratos() -> None:
    st.header("Contratos e fornecedores (tarefa 3.2 — amostra de 15 instituições)")
    df = carregar("contratos_mec.parquet")
    if df.empty:
        st.warning("dados/contratos_mec.parquet não encontrado.")
        return
    orgao = st.selectbox("Órgão", sorted(df["orgao"].unique()))
    recorte = df[df["orgao"] == orgao]
    st.metric("Contratos", len(recorte))
    top = (
        recorte.groupby("fornecedorNome", dropna=False)["valorFinalCompra"]
        .agg(["sum", "size"])
        .rename(columns={"sum": "valor_total", "size": "n_contratos"})
        .sort_values("valor_total", ascending=False)
        .head(15)
    )
    st.subheader("Top 15 fornecedores por valor")
    st.bar_chart(top["valor_total"])
    st.dataframe(top, width="stretch")
    st.caption("Valores nominais dos contratos 2023–2025 (janela do piloto da Fase 3).")


def pagina_ibge() -> None:
    st.header("Cruzamentos com o IBGE (tarefa 4.4)")
    per_capita = carregar("per_capita_nacional.csv")
    emendas_uf = carregar("emendas_per_capita_uf.csv")
    if per_capita.empty or emendas_uf.empty:
        st.warning("Rode analises/00b_baixar_ibge.py e analises/14_ibge_cruzamento.py antes.")
        return
    st.subheader("Despesa real per capita — subfunção 364, Brasil")
    st.line_chart(per_capita.set_index("ano")["per_capita_real"])
    st.caption("População de 2022–2023 interpolada (sem estimativa publicada no agregado 6579).")
    st.subheader("Emendas pagas per capita por UF (2014–2025, R$ de 2025)")
    st.bar_chart(emendas_uf.set_index("sigla_uf")["per_capita_real"])
    atipicas = emendas_uf[emendas_uf["flag_atipico"]]
    if not atipicas.empty:
        st.markdown("**UFs atípicas** (z-score robusto |z| > 3,5): "
                    + ", ".join(atipicas["sigla_uf"]))


PAGINAS = {
    "Séries por instituição": pagina_series,
    "Mapa de flags": pagina_mapa_flags,
    "Casos priorizados": pagina_casos,
    "Contratos e fornecedores": pagina_contratos,
    "Cruzamentos IBGE": pagina_ibge,
}


def main() -> None:
    st.set_page_config(page_title="Sucuri — Despesas com Ensino Superior", layout="wide")
    st.sidebar.title("Sucuri")
    st.sidebar.info(AVISO_METODOLOGICO)
    escolha = st.sidebar.radio("Página", list(PAGINAS))
    PAGINAS[escolha]()


main()
