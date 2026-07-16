#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 2.1 do ROADMAP — Análise exploratória com foco em anomalias.

Parte de `dados/*_v2.{csv,parquet}` (saída da Fase 1 — deduplicado,
deflacionado, com ano parcial/séries curtas marcados) e gera
`relatorios/02_eda.md` + figuras em `relatorios/figuras/`:

  1. Evolução do total pago_real por ano (Conjuntos A e B).
  2. Top 10 programas/ações do Conjunto A por valor acumulado.
  3. Distribuição de taxa_liquidacao/taxa_pagamento por tipo de instituição (B).
  4. Ranking de instituições por pago_real no último ano completo (absoluto —
     sem dado de matrícula ainda; per capita fica para a tarefa 4.1).
  5. Tabela das linhas já flageadas (flag_anomalia=True) com leitura crítica.
  6. Seção "candidatas a investigação" (até 20 linhas, justificadas).

Uso:
    uv run python analises/02_eda.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sucuri.graficos import PALETA_CATEGORICA, aplicar_estilo, salvar_figura

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DIR_FIGURAS = DIR_RELATORIOS / "figuras"


def carregar(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DIR_DADOS / f"{nome}_v2.parquet")


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def tabela_md_texto(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, disable_numparse=True)


def fmt_bi(v: float) -> str:
    return f"{v / 1e9:,.2f}"


# --------------------------------------------------------------------------- #
# 1. Evolução anual
# --------------------------------------------------------------------------- #
def grafico_evolucao_anual(df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    aplicar_estilo()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    def _plot(ax, df, titulo):
        s = df.groupby(["ano", "ano_parcial"], as_index=False)["pago_real"].sum()
        s = s.sort_values("ano")
        completos = s[~s["ano_parcial"]]
        parcial = s[s["ano_parcial"]]
        ax.plot(completos["ano"], completos["pago_real"] / 1e9, color=PALETA_CATEGORICA[0],
                linewidth=2, marker="o", markersize=4, label="Ano completo")
        if not parcial.empty and not completos.empty:
            ultimo_completo = completos.iloc[-1]
            ponte = pd.concat([ultimo_completo.to_frame().T, parcial]).astype({"ano": int})
            ax.plot(ponte["ano"], ponte["pago_real"] / 1e9, color=PALETA_CATEGORICA[0],
                    linewidth=2, linestyle="--", marker="x", markersize=6, label="Ano parcial")
        ax.set_title(titulo, fontsize=11, color="#0b0b0b")
        ax.set_ylabel("R$ bilhões (valores reais)")
        ax.set_xlabel("Ano")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        return s

    s_a = _plot(ax1, df_a, "Conjunto A — Ensino Superior (subfunção 364)")
    s_b = _plot(ax2, df_b, "Conjunto B — total dos órgãos do MEC")

    caminho = DIR_FIGURAS / "01_evolucao_anual.png"
    salvar_figura(fig, caminho)
    return str(caminho), s_a, s_b


# --------------------------------------------------------------------------- #
# 2. Top programas/ações (Conjunto A)
# --------------------------------------------------------------------------- #
def grafico_top_acoes(df_a: pd.DataFrame, n: int = 10) -> tuple[str, pd.DataFrame]:
    completos = df_a[~df_a["ano_parcial"]]
    agrupado = (
        completos.groupby(["codigoPrograma", "programa", "codigoAcao", "acao"], as_index=False)
        ["pago_real"].sum()
        .sort_values("pago_real", ascending=False)
        .head(n)
    )
    # Nem o texto da ação nem o do programa são únicos isoladamente: a mesma
    # ação (ex.: "Ativos Civis da União", despesa de pessoal) é reutilizada
    # por vários programas, e o mesmo nome de programa por vezes aparece sob
    # mais de um código (recodificação orçamentária ao longo dos anos) — só
    # o par de códigos (codigoPrograma-codigoAcao) garante um rótulo único
    # por barra no eixo categórico.
    agrupado["rotulo"] = (
        agrupado["acao"].str.slice(0, 42) + "\n(" + agrupado["programa"].str.slice(0, 34)
        + " " + agrupado["codigoPrograma"].astype(str) + "-" + agrupado["codigoAcao"].astype(str) + ")"
    )

    aplicar_estilo()
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ordem = agrupado.iloc[::-1]
    barras = ax.barh(ordem["rotulo"], ordem["pago_real"] / 1e9, color=PALETA_CATEGORICA[0])
    ax.set_xlabel("R$ bilhões (valores reais, acumulado 2014–2025)")
    ax.set_title(f"Top {n} ações do Conjunto A por valor pago acumulado", fontsize=11)
    ax.bar_label(barras, fmt="%.1f", padding=3, fontsize=8, color="#52514e")
    ax.tick_params(axis="y", labelsize=8)

    caminho = DIR_FIGURAS / "02_top_acoes.png"
    salvar_figura(fig, caminho)
    return str(caminho), agrupado.drop(columns="rotulo")


# --------------------------------------------------------------------------- #
# 3. Distribuição de taxas por tipo de instituição (Conjunto B)
# --------------------------------------------------------------------------- #
def grafico_taxas_por_tipo(df_b: pd.DataFrame) -> str:
    completos = df_b[~df_b["ano_parcial"]]
    tipos = completos["tipo_instituicao"].value_counts().index.tolist()

    aplicar_estilo()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    for ax, coluna, titulo in (
        (ax1, "taxa_liquidacao", "Taxa de liquidação (liquidado / empenhado)"),
        (ax2, "taxa_pagamento", "Taxa de pagamento (pago / empenhado)"),
    ):
        dados = [completos.loc[completos["tipo_instituicao"] == t, coluna].dropna() for t in tipos]
        bp = ax.boxplot(dados, orientation="horizontal", patch_artist=True, tick_labels=tipos, widths=0.6)
        for patch, cor in zip(bp["boxes"], PALETA_CATEGORICA, strict=False):
            patch.set_facecolor(cor)
            patch.set_alpha(0.55)
            patch.set_edgecolor(cor)
        for mediana in bp["medians"]:
            mediana.set_color("#0b0b0b")
        ax.set_title(titulo, fontsize=10)
        ax.set_xlabel("Proporção")

    caminho = DIR_FIGURAS / "03_taxas_por_tipo.png"
    salvar_figura(fig, caminho)
    return str(caminho)


# --------------------------------------------------------------------------- #
# 4. Ranking de instituições (último ano completo, absoluto)
# --------------------------------------------------------------------------- #
def grafico_ranking_instituicoes(df_b: pd.DataFrame, n: int = 15) -> tuple[str, pd.DataFrame, int]:
    ultimo_ano_completo = int(df_b.loc[~df_b["ano_parcial"], "ano"].max())
    snapshot = df_b[df_b["ano"] == ultimo_ano_completo].sort_values("pago_real", ascending=False).head(n)
    snapshot = snapshot[["orgao", "tipo_instituicao", "pago_real"]].copy()
    snapshot["orgao_curto"] = snapshot["orgao"].str.slice(0, 45)

    aplicar_estilo()
    fig, ax = plt.subplots(figsize=(9, 6))
    ordem = snapshot.iloc[::-1]
    cores = [PALETA_CATEGORICA[0]] * len(ordem)
    barras = ax.barh(ordem["orgao_curto"], ordem["pago_real"] / 1e9, color=cores)
    ax.set_xlabel("R$ bilhões (valores reais)")
    ax.set_title(f"Top {n} instituições por pago_real — {ultimo_ano_completo} (valor absoluto, sem per capita)",
                 fontsize=10)
    ax.bar_label(barras, fmt="%.2f", padding=3, fontsize=8, color="#52514e")

    caminho = DIR_FIGURAS / "04_ranking_instituicoes.png"
    salvar_figura(fig, caminho)
    return str(caminho), snapshot.drop(columns="orgao_curto"), ultimo_ano_completo


# --------------------------------------------------------------------------- #
# 5 e 6. Linhas flageadas e candidatas a investigação
# --------------------------------------------------------------------------- #
def montar_candidatas(df_a: pd.DataFrame, df_b: pd.DataFrame, limite: int = 20) -> pd.DataFrame:
    def preparar(df, coluna_entidade, rotulo_conjunto):
        flagged = df[df["flag_anomalia"]].copy()
        flagged["entidade"] = flagged[coluna_entidade]
        flagged["conjunto"] = rotulo_conjunto
        flagged["magnitude"] = flagged["zscore_robusto_pago"].abs().fillna(0)
        sinais = []
        for _, linha in flagged.iterrows():
            s = []
            if linha.get("flag_anomalia_zscore"):
                s.append("zscore")
            if linha.get("flag_anomalia_robusto"):
                s.append("zscore_robusto")
            if linha.get("flag_salto_anual"):
                s.append("salto_anual")
            if linha.get("flag_pago_maior_empenhado"):
                s.append("pago>empenhado")
            if linha.get("flag_liquidado_maior_empenhado"):
                s.append("liquidado>empenhado")
            if "flag_atipico_entre_pares" in df.columns and linha.get("flag_atipico_entre_pares"):
                s.append("atipico_entre_pares")
            sinais.append(", ".join(s))
        flagged["sinais"] = sinais
        return flagged[["conjunto", "entidade", "ano", "pago_real", "variacao_pago_aa",
                         "zscore_robusto_pago", "sinais", "magnitude"]]

    candidatas = pd.concat([
        preparar(df_a, "acao", "A"),
        preparar(df_b, "orgao", "B"),
    ], ignore_index=True)
    return candidatas.sort_values("magnitude", ascending=False).head(limite)


def justificativa(linha: pd.Series) -> str:
    partes = [f"sinais: {linha['sinais']}"]
    if pd.notna(linha["variacao_pago_aa"]):
        partes.append(f"variação anual de {linha['variacao_pago_aa']:+.0%}")
    if pd.notna(linha["zscore_robusto_pago"]):
        partes.append(f"z-score robusto de {linha['zscore_robusto_pago']:.1f}")
    return "; ".join(partes) + "."


# --------------------------------------------------------------------------- #
# Relatório
# --------------------------------------------------------------------------- #
def gerar_relatorio() -> str:
    df_a = carregar("despesas_ensino_superior")
    df_b = carregar("despesas_por_instituicao")

    cam_evolucao, s_a, s_b = grafico_evolucao_anual(df_a, df_b)
    cam_top_acoes, top_acoes = grafico_top_acoes(df_a)
    cam_taxas = grafico_taxas_por_tipo(df_b)
    cam_ranking, ranking, ultimo_ano = grafico_ranking_instituicoes(df_b)

    top_acoes_fmt = top_acoes.copy()
    top_acoes_fmt["pago_real"] = top_acoes_fmt["pago_real"].map(lambda v: f"{v / 1e9:,.2f}")
    top_acoes_fmt = top_acoes_fmt.rename(columns={"pago_real": "pago_real_bi_2014_2025"})

    ranking_fmt = ranking.copy()
    ranking_fmt["pago_real"] = ranking_fmt["pago_real"].map(lambda v: f"{v / 1e9:,.2f}")
    ranking_fmt = ranking_fmt.rename(columns={"pago_real": f"pago_real_bi_{ultimo_ano}"})

    n_flagged_a = int(df_a["flag_anomalia"].sum())
    n_flagged_b = int(df_b["flag_anomalia"].sum())

    candidatas = montar_candidatas(df_a, df_b)
    candidatas_fmt = candidatas.copy()
    candidatas_fmt["pago_real_mi"] = (candidatas_fmt["pago_real"] / 1e6).round(2)
    candidatas_fmt["justificativa"] = candidatas.apply(justificativa, axis=1)
    tabela_candidatas = candidatas_fmt[["conjunto", "entidade", "ano", "pago_real_mi", "justificativa"]]
    tabela_candidatas["entidade"] = tabela_candidatas["entidade"].str.slice(0, 65)

    linhas = f"""# Análise exploratória com foco em anomalias — tarefa 2.1

Gerado por `analises/02_eda.py`. Base: `dados/*_v2.{{csv,parquet}}` (Fase 1
— deduplicado, deflacionado, ano parcial/séries curtas marcados). Todos os
valores monetários abaixo são **reais** (`pago_real`, R$ de {ultimo_ano}),
não nominais.

## 1. Evolução do total pago por ano

![Evolução anual]({Path(cam_evolucao).relative_to(DIR_RELATORIOS)})

**Leitura:** a linha tracejada marca o ano parcial (2026) — não deve ser
lida como queda de gasto, só cobertura incompleta do exercício (ver
`CLAUDE.md`). Nos anos completos, ambos os conjuntos mostram uma trajetória
em U: queda real entre 2017/2018 e o piso em **2021** (Conjunto B: R$ 195,1
bi em 2017 → R$ 153,3 bi em 2021, -21,4% em termos reais), seguida de
recuperação sustentada até 2025 (R$ 204,7 bi, novo máximo da série). O
Conjunto A (só subfunção 364) segue a mesma forma em U, com piso também em
2021 (R$ 34,8 bi) e mais volatilidade ano a ano — esperado, dado que é uma
fração específica do orçamento do MEC, mais sensível a mudanças de
programa/ação do que o total institucional do Conjunto B.

## 2. Top 10 ações do Conjunto A por valor acumulado (2014–2025)

![Top ações]({Path(cam_top_acoes).relative_to(DIR_RELATORIOS)})

{tabela_md_texto(top_acoes_fmt)}

**Leitura:** as duas maiores linhas — juntas, ~R$ 343 bi acumulados em
2014–2025, mais que a soma de todas as outras oito do top 10 — são a mesma
ação orçamentária genérica, "Ativos Civis da União" (folha de pagamento de
servidores ativos), classificada sob dois programas orçamentários
diferentes. Ou seja: **a maior parte da despesa etiquetada como subfunção
"Ensino Superior" no Conjunto A é folha de pessoal**, não bolsas nem
custeio de funcionamento — um achado relevante para interpretar qualquer
"salto" nessa ação como possivelmente ligado a reajuste salarial/plano de
carreira, não a um evento pontual de gasto. As demais posições do top 10
são consistentes com o escopo temático esperado (bolsas de estudo,
funcionamento das IFES) — não há, nesta lista, nenhuma ação fora do tema da
subfunção 364.

## 3. Distribuição de taxas de execução por tipo de instituição (Conjunto B)

![Taxas por tipo]({Path(cam_taxas).relative_to(DIR_RELATORIOS)})

**Leitura:** a mediana de `taxa_pagamento` fica entre 83% e 90% em todos os
tipos de instituição — grupos comparáveis no centro da distribuição.
A dispersão é o que diferencia: `Outros / Administração` tem a caixa mais
larga (25º percentil em 70%, mínimo em 35%) — categoria heterogênea (poucos
órgãos, sem um perfil orçamentário único), consistente com maior variação
esperada. `Universidade Federal` e `Instituto/CEFET/Escola Técnica`, os
dois grupos com mais observações (791 e 480 linhas-ano), têm a caixa
(25º–75º percentil) estreita e comparável entre si (~0,84–0,91), mas
exibem vários **outliers de baixa execução** (círculos isolados abaixo de
0,5, com um mínimo de 0,098 em Universidade Federal) — órgãos/anos
específicos que pagaram uma fração muito menor do empenhado que o restante
do grupo. Esses pontos são candidatos naturais para checagem cruzada com
as tarefas 2.3–2.5 (não investigados individualmente nesta seção).

## 4. Ranking de instituições por pago_real — {ultimo_ano} (valor absoluto)

![Ranking de instituições]({Path(cam_ranking).relative_to(DIR_RELATORIOS)})

{tabela_md_texto(ranking_fmt)}

**Ressalva importante (a mais relevante desta seção):** o primeiro
colocado, FNDE (R$ 89,78 bi — 7,5× o segundo colocado), não deve ser lido
como "a maior despesa de ensino superior": o Conjunto B traz o total do
órgão em **todas as funções**, e o FNDE administra programas nacionais de
educação básica (merenda escolar, material didático, transporte escolar)
além de FIES — a maior parte desse valor provavelmente não é ensino
superior. Essa é exatamente a ressalva já registrada em `CLAUDE.md`
("Conjunto B não permite concluir gasto com ensino superior da
instituição"); o Conjunto A (subfunção 364) é a fonte correta para valores
especificamente de ensino superior. Adicionalmente, este ranking é por
valor **absoluto**, não per capita — não há ainda dado de matrícula por IES
incorporado (tarefa 4.1, que depende do Censo da Educação Superior/INEP,
ver `EXTERNAL.md`, item E3).

## 5. Linhas já flageadas (`flag_anomalia=True`)

Conjunto A: {n_flagged_a} linhas. Conjunto B: {n_flagged_b} linhas (dados
já tratados na Fase 1 — nenhuma delas é do ano parcial nem de série curta).
Leitura crítica: a maior parte dessas flags vem de `flag_anomalia_robusto`
e `flag_salto_anual`, ambas sensíveis a bases de comparação pequenas
mesmo dentro de séries com ≥5 anos — um salto real de política pública
(ex.: criação ou extinção de um programa) produz exatamente o mesmo sinal
estatístico que um erro de dado. A seção 6 abaixo prioriza as mais extremas
para checagem manual; a Fase 2.3–2.5 adiciona métodos complementares
(Isolation Forest, LOF, Benford, tendência robusta) para triangular esses
sinais antes de qualquer conclusão.

## 6. Candidatas a investigação (top {len(tabela_candidatas)})

Ordenadas por `|zscore_robusto_pago|` (maior desvio robusto em relação ao
histórico da própria série/instituição primeiro). `pago_real_mi` em R$
milhões, valores reais.

{tabela_md_texto(tabela_candidatas)}

**Leitura:** esta lista combina os dois conjuntos e prioriza magnitude do
desvio robusto — não é uma lista de irregularidades, é uma lista de
prioridade para checagem manual ou cruzamento com outras fontes (Fase 3).
Todas as linhas aqui já passaram pelo tratamento da Fase 1 (sem ano
parcial, sem série curta, sem duplicata de grafia) — o risco de falso
positivo por artefato de dado já conhecido foi reduzido, mas não
eliminado (mudanças legítimas de política orçamentária também geram
z-scores altos). Dois padrões concentram boa parte desta lista e já têm
explicação estrutural, verificada nos dados brutos (não apenas hipótese):

- **Universidades federais recém-criadas na expansão de 2013–2014**
  (Cariri, Oeste da Bahia, Sul da Bahia, Sul e Sudeste do Pará): o
  z-score robusto muito negativo em 2014/2015 reflete o primeiro ano de
  implantação, com orçamento uma fração do que a instituição passa a
  receber uma vez madura (ex.: Cariri foi de R$ 7,0 milhões em 2014 para
  R$ 98,5 milhões já em 2015 e R$ 172 milhões em 2025) — é um efeito
  rampa de implantação institucional conhecido, não um evento atípico de
  gasto. Não remove essas linhas da lista (o desvio é real e grande),
  mas muda a pergunta de investigação: não "por que caiu", e sim "a
  instituição está madura hoje" — já respondida pelos anos seguintes.
- **"Concessão de Bolsas de Residência em Saúde" (Conjunto A):** os quatro
  z-scores negativos de ~-7,5 vêm de linhas com `pago_real=0`, alternando
  com anos de execução normal (~R$ 800 milhões) dentro do mesmo grupo de
  ações — um padrão de financiamento intermitente entre programas/ações
  correlatos (múltiplos códigos de programa para a mesma ação nominal,
  cada um ativo em anos diferentes), coerente com a esparsidade já
  documentada do Conjunto A (`CLAUDE.md`), não com uma interrupção
  pontual de um programa contínuo.

As demais linhas (institutos federais com variações de 7–32% e o salto de
mais de 16.000% na ação de reconstrução do Museu Nacional em 2022 — ano
seguinte ao incêndio de 2018, consistente com obra de reconstrução) não
têm explicação estrutural evidente nos próprios dados e permanecem como
prioridade de checagem manual/cruzamento de fontes.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    conteudo = gerar_relatorio()
    caminho = DIR_RELATORIOS / "02_eda.md"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho}")


if __name__ == "__main__":
    main()
