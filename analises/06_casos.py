#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 2.5 do ROADMAP — Consolidação e priorização de casos.

Unifica os sinais das tarefas 2.1–2.4 em uma tabela de casos por
(conjunto, entidade, ano):

  - `sinal_flag`: 1.0 se `flag_anomalia` (Fase 1) é True, senão 0.0.
  - `sinal_outlier`: `score_anomalia` da tarefa 2.3 (Isolation Forest + LOF,
    já normalizado 0–1 dentro do grupo/tipo_instituicao), quando a linha
    foi elegível para os modelos.
  - `sinal_serie`: desvio padronizado da tarefa 2.4 (Theil–Sen),
    normalizado por rank em [0, 1] entre os eventos detectados — só
    existe para o Conjunto B (2.4 não roda sobre o Conjunto A).

`score_combinado` = média dos sinais disponíveis (ignora os que não se
aplicam à linha, não trata ausência como zero). Linhas de ano parcial são
excluídas de toda a análise nesta tarefa (nenhum caso pode se basear em
ano parcial — critério de aceite do ROADMAP).

Salva `dados/casos_priorizados.csv` e `relatorios/06_casos.md` (top 15,
com justificativa textual e anotação de padrões estruturais já
identificados nas tarefas 2.1–2.4, para não repetir como "achado novo"
algo já explicado).

Uso:
    uv run python analises/06_casos.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")

# Padrões estruturais já identificados e explicados nas tarefas 2.1–2.4 —
# ver relatorios/02_eda.md (seção 6), relatorios/04_outliers.md (seção 3) e
# relatorios/05_series.md (seção 4). Casos que batem aqui recebem uma nota
# no relatório em vez de serem apresentados como achado novo.
UNIVERSIDADES_EXPANSAO_2013_2014 = [
    "Universidade Federal do Cariri",
    "Universidade Federal do Oeste da Bahia",
    "Universidade Federal do Sul da Bahia",
    "Universidade Federal do Sul e Sudeste do Pará",
]
ACAO_FOLHA_PESSOAL = "ATIVOS CIVIS DA UNIAO"
ORGAO_DOMINANCIA_ESCALA = "Universidade Federal do Rio de Janeiro"


def carregar_v2(nome: str) -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / f"{nome}_v2.parquet")
    return df[~df["ano_parcial"]].copy()


def carregar_scores(nome: str) -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / f"{nome}_scores.parquet")
    return df[~df["ano_parcial"]][["chave_serie", "ano", "score_anomalia"]].copy()


def carregar_eventos_series() -> pd.DataFrame:
    df = pd.read_csv(DIR_DADOS / "eventos_series.csv", dtype={"chave_serie": str})
    df["sinal_serie"] = df["desvio_padronizado"].abs().rank(pct=True)
    return df[["chave_serie", "ano", "sinal_serie", "desvio_padronizado"]]


def descrever_sinais(linha: pd.Series) -> str:
    partes = []
    for col, rotulo in (
        ("flag_anomalia_zscore", "zscore"),
        ("flag_anomalia_robusto", "zscore_robusto"),
        ("flag_salto_anual", "salto_anual"),
        ("flag_pago_maior_empenhado", "pago>empenhado"),
        ("flag_liquidado_maior_empenhado", "liquidado>empenhado"),
        ("flag_atipico_entre_pares", "atipico_entre_pares"),
    ):
        if col in linha.index and bool(linha.get(col, False)):
            partes.append(rotulo)
    if pd.notna(linha.get("score_anomalia_2_3")):
        partes.append(f"outlier_multivariado(score={linha['score_anomalia_2_3']:.2f})")
    if pd.notna(linha.get("desvio_padronizado")):
        partes.append(f"tendencia_robusta(desvio={linha['desvio_padronizado']:.1f})")
    return ", ".join(partes) if partes else "(nenhuma flag de regra — só modelo multivariado/tendência)"


def nota_padrao_conhecido(conjunto: str, entidade: str) -> str | None:
    if conjunto == "B" and entidade in UNIVERSIDADES_EXPANSAO_2013_2014:
        return ("Padrão já identificado: universidade da expansão federal 2013–2014 — "
                "orçamento de implantação baixo no(s) primeiro(s) ano(s), não evento atípico "
                "(ver relatorios/02_eda.md, seção 6).")
    if conjunto == "A" and entidade == ACAO_FOLHA_PESSOAL:
        return ("Padrão já identificado: ação genérica de folha de pagamento (\"Ativos Civis "
                "da União\"), maior linha do Conjunto A por construção — variações tendem a "
                "refletir reajuste salarial/plano de carreira, não evento pontual "
                "(ver relatorios/02_eda.md, seção 2).")
    if conjunto == "B" and entidade == ORGAO_DOMINANCIA_ESCALA:
        return ("Padrão já identificado: UFRJ é uma das maiores universidades do grupo — "
                "outlier multivariado pode refletir dominância de escala, não comportamento "
                "atípico de execução (ver relatorios/04_outliers.md, seção 3).")
    return None


def justificativa(linha: pd.Series) -> str:
    nota = nota_padrao_conhecido(linha["conjunto"], linha["entidade"])
    base = f"Sinais: {linha['sinais']}. Score combinado: {linha['score_combinado']:.2f} (de {linha['n_sinais']} sinal(is))."
    return f"{nota} {base}" if nota else base


def montar_casos() -> pd.DataFrame:
    linhas = []
    for conjunto, nome, coluna_entidade in (
        ("A", "despesas_ensino_superior", "acao"),
        ("B", "despesas_por_instituicao", "orgao"),
    ):
        v2 = carregar_v2(nome)
        scores = carregar_scores(nome).rename(columns={"score_anomalia": "score_anomalia_2_3"})
        df = v2.merge(scores, on=["chave_serie", "ano"], how="left")

        if conjunto == "B":
            eventos = carregar_eventos_series()
            df = df.merge(eventos, on=["chave_serie", "ano"], how="left")
        else:
            df["sinal_serie"] = pd.NA
            df["desvio_padronizado"] = pd.NA

        df["conjunto"] = conjunto
        df["entidade"] = df[coluna_entidade]
        df["sinal_flag"] = df["flag_anomalia"].astype(float)
        df["sinal_outlier"] = df["score_anomalia_2_3"]

        sinais = df[["sinal_flag", "sinal_outlier", "sinal_serie"]].apply(pd.to_numeric, errors="coerce")
        df["n_sinais"] = sinais.notna().sum(axis=1)
        df["score_combinado"] = sinais.mean(axis=1, skipna=True)
        df["sinais"] = df.apply(descrever_sinais, axis=1)

        linhas.append(df[["conjunto", "entidade", "ano", "pago_real", "score_combinado",
                           "n_sinais", "sinais", "desvio_padronizado", "score_anomalia_2_3",
                           "sinal_flag", "sinal_outlier"]])

    casos = pd.concat(linhas, ignore_index=True)
    # "Disparar" é um critério discreto, não "score > 0" — score_anomalia
    # (2.3) é um rank contínuo em (0, 1] quase sempre positivo para
    # qualquer linha elegível, então esse teste sozinho deixaria passar
    # quase tudo. Considera-se candidato quem tem flag_anomalia=True
    # (Fase 1), OU está no top 10% de score_anomalia do seu grupo (2.3),
    # OU aparece em eventos_series.csv (2.4 — já é, por construção, um
    # evento acima do limiar de desvio).
    LIMIAR_OUTLIER_TOP10PCT = 0.90
    disparou = (
        (casos["sinal_flag"] > 0)
        | (casos["sinal_outlier"].fillna(0) >= LIMIAR_OUTLIER_TOP10PCT)
        | casos["desvio_padronizado"].notna()
    )
    casos = casos[disparou]
    # Ordenação primária por número de sinais concordantes, não só pelo
    # score: a média de um único sinal binário (flag_anomalia=1.0) empata
    # em 1.00 com casos de 2-3 sinais próximos do máximo, o que enterraria
    # a triangulação de métodos independentes — exatamente o que dá mais
    # confiança a um caso — atrás de flags isoladas.
    return casos.sort_values(["n_sinais", "score_combinado"], ascending=[False, False]).reset_index(drop=True)


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def distribuicao_por_ano(casos: pd.DataFrame) -> tuple[int, float, int, int]:
    contagem_2025 = int((casos["ano"] == 2025).sum())
    pct_2025 = contagem_2025 / len(casos) if len(casos) else 0.0
    triangulados = casos[casos["n_sinais"] == casos["n_sinais"].max()]
    triangulados_2025 = int((triangulados["ano"] == 2025).sum())
    return contagem_2025, pct_2025, triangulados_2025, len(triangulados)


def gerar_relatorio(casos: pd.DataFrame) -> str:
    top15 = casos.head(15).copy()
    top15["justificativa"] = top15.apply(justificativa, axis=1)
    top15["pago_real_mi"] = (top15["pago_real"] / 1e6).round(2)
    top15["entidade_curta"] = top15["entidade"].str.slice(0, 45)
    top15["score_combinado"] = top15["score_combinado"].round(3)

    linhas_texto = []
    for i, linha in enumerate(top15.itertuples(), start=1):
        linhas_texto.append(
            f"**{i}. {linha.entidade_curta} — {linha.ano}** (Conjunto {linha.conjunto}, "
            f"R$ {linha.pago_real_mi:,.2f} milhões reais, score {linha.score_combinado:.2f})\n"
            f"   {linha.justificativa}"
        )
    lista_top15 = "\n\n".join(linhas_texto)

    n_conjunto_a = int((casos["conjunto"] == "A").sum())
    n_conjunto_b = int((casos["conjunto"] == "B").sum())
    n_com_2_mais_sinais = int((casos["n_sinais"] >= 2).sum())
    n_2025, pct_2025, n_triangulados_2025, n_triangulados = distribuicao_por_ano(casos)

    linhas = f"""# Consolidação e priorização de casos — tarefa 2.5

Gerado por `analises/06_casos.py`. Unifica sinais das tarefas 2.1–2.4:
flag_anomalia (Fase 1), score de outliers multivariados (2.3, Isolation
Forest + LOF) e desvio de tendência robusta (2.4, Theil–Sen — só Conjunto
B). A Lei de Benford (2.2) não entra aqui: é um teste de conformidade do
**conjunto/grupo** como um todo, não produz um sinal por entidade/ano (ver
`relatorios/03_benford.md`). **Ano parcial excluído de toda a análise desta
tarefa.**

`score_combinado` = média dos sinais disponíveis para a linha, cada um em
[0, 1] (1 = mais anômalo): `flag_anomalia` (binário: 0 ou 1),
`score_anomalia` de 2.3, e — só para o Conjunto B — o rank percentual do
desvio de 2.4 entre os eventos detectados. Só entram na tabela linhas em
que pelo menos um sinal **disparou** de fato: `flag_anomalia=True`, ou
`score_anomalia` no top 10% do seu grupo (2.3), ou presença em
`eventos_series.csv` (2.4). `score_anomalia` isolado sendo positivo não
basta — é um rank contínuo quase sempre > 0 para qualquer linha elegível,
não um indicador de disparo.

Casos candidatos totais: {len(casos)} ({n_conjunto_a} no Conjunto A,
{n_conjunto_b} no Conjunto B). {n_com_2_mais_sinais} casos têm 2 ou mais
sinais concordando — esses merecem prioridade adicional na checagem
manual, por triangulação de métodos independentes.

## Top 15 casos priorizados

{lista_top15}

## Tabela completa (top 15)

{tabela_md(top15[["conjunto", "entidade_curta", "ano", "pago_real_mi", "score_combinado", "n_sinais", "sinais"]])}

## Leitura geral

Esta lista prioriza checagem manual e cruzamento com fontes externas (Fase
3 do ROADMAP: contratos, licitações, sanções, convênios) — **não é uma
lista de irregularidades**. Casos marcados com nota de "padrão já
identificado" têm explicação estrutural razoável encontrada nas próprias
tarefas 2.1–2.4 (universidades novas em rampa de implantação, ação
genérica de folha de pagamento, dominância de escala) e devem ser
priorizados por último dentro desta lista, mesmo com score alto — o score
combinado não sabe distinguir "estatisticamente extremo" de "já explicado
por contexto conhecido"; essa distinção só existe porque as tarefas
anteriores investigaram manualmente cada padrão recorrente. Os casos sem
nota não têm explicação estrutural encontrada até aqui e são a prioridade
real de investigação desta fase.

**Achado adicional desta consolidação, não visível em nenhuma tarefa
anterior isoladamente:** 2025 responde por {n_2025} dos {len(casos)} casos
({pct_2025:.0%}, bem acima dos ~8% esperados se os casos se distribuíssem
igualmente entre os 12 anos completos) e por {n_triangulados_2025} dos
{n_triangulados} casos com o número máximo de sinais concordantes — quase
metade da camada de maior confiança. Isso é consistente com o achado da
tarefa 2.1 (`relatorios/02_eda.md`, seção 1) de que 2025 é o novo máximo
real da série tanto no Conjunto A quanto no B, após a recuperação pós-2021.
**Leitura recomendada:** boa parte dos casos de 2025 provavelmente não são
{n_2025} eventos independentes, e sim a mesma tendência macro de
recuperação/crescimento real do orçamento do MEC se manifestando
instituição por instituição — cada modelo de tendência (Theil–Sen) vê
apenas sua própria série e não tem como saber que o aumento é generalizado.
Isso não invalida os casos individuais (o aumento pode ainda ser
desproporcional em alguns deles), mas muda a pergunta de "por que esta
instituição teve um salto" para "esta instituição cresceu mais que a média
do setor em 2025, e por quê" — uma investigação comparativa, não isolada.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    casos = montar_casos()

    caminho_csv = DIR_DADOS / "casos_priorizados.csv"
    casos.to_csv(caminho_csv, index=False, encoding="utf-8")
    print(f"Salvo: {caminho_csv} ({len(casos)} casos)")

    conteudo = gerar_relatorio(casos)
    caminho_md = DIR_RELATORIOS / "06_casos.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
