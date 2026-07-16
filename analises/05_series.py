#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 2.4 do ROADMAP — Séries temporais por instituição (Theil–Sen).

Para cada órgão do Conjunto B com ≥8 anos elegíveis (exclui ano parcial),
ajusta uma tendência robusta de Theil–Sen sobre `pago_real` e sinaliza
pontos com resíduo padronizado (robusto, MAD) acima de 2,5 desvios.
Compara com `flag_salto_anual` (Fase 1) — mesmo fenômeno (mudança de
patamar), métodos diferentes (resíduo à tendência de longo prazo vs.
variação ano a ano).

Salva `dados/eventos_series.csv` (até ~50 eventos, ordenados por desvio) e
`relatorios/05_series.md`.

Uso:
    uv run python analises/05_series.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sucuri.graficos import PALETA_CATEGORICA, aplicar_estilo, salvar_figura
from sucuri.tendencias import ajustar_theil_sen, detectar_eventos_serie

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DIR_FIGURAS = DIR_RELATORIOS / "figuras"
MIN_ANOS = 8
LIMIAR_DESVIO = 2.5
MAX_EVENTOS = 50


def carregar() -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / "despesas_por_instituicao_v2.parquet")
    return df[~df["ano_parcial"]]


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def grafico_exemplos(df: pd.DataFrame, eventos: pd.DataFrame, n_exemplos: int = 4) -> str:
    """Gráfico de tendência + pontos observados para os `n_exemplos` maiores eventos."""
    if eventos.empty:
        return ""
    orgaos_exemplo = eventos["chave_serie"].drop_duplicates().head(n_exemplos).tolist()

    aplicar_estilo()
    fig, eixos = plt.subplots(1, len(orgaos_exemplo), figsize=(4.2 * len(orgaos_exemplo), 4))
    if len(orgaos_exemplo) == 1:
        eixos = [eixos]

    for ax, chave in zip(eixos, orgaos_exemplo, strict=False):
        serie = df[df["chave_serie"] == chave].sort_values("ano")
        anos = serie["ano"].to_numpy(dtype=float)
        valores = serie["pago_real"].to_numpy(dtype=float)
        inclinacao, intercepto = ajustar_theil_sen(anos, valores)
        preditos = intercepto + inclinacao * anos

        nome_curto = serie["orgao"].iloc[0][:30]
        ax.plot(anos, valores / 1e6, "o-", color=PALETA_CATEGORICA[0], label="Observado", markersize=4)
        ax.plot(anos, preditos / 1e6, "--", color=PALETA_CATEGORICA[7], label="Tendência (Theil–Sen)")

        eventos_orgao = eventos[eventos["chave_serie"] == chave]
        ax.scatter(eventos_orgao["ano"], eventos_orgao["pago_real"] / 1e6,
                    color=PALETA_CATEGORICA[7], zorder=5, s=60, marker="x")

        ax.set_title(nome_curto, fontsize=9)
        ax.set_xlabel("Ano")
        ax.set_ylabel("R$ milhões (reais)")
        ax.legend(frameon=False, fontsize=7)

    caminho = DIR_FIGURAS / "07_eventos_series.png"
    salvar_figura(fig, caminho)
    return str(caminho)


def gerar_relatorio(df: pd.DataFrame, eventos: pd.DataFrame, n_series_elegiveis: int) -> str:
    eventos_limitados = eventos.head(MAX_EVENTOS).copy()
    eventos_fmt = eventos_limitados.merge(
        df[["chave_serie", "orgao", "tipo_instituicao"]].drop_duplicates(), on="chave_serie", how="left"
    )
    eventos_fmt["pago_real_mi"] = (eventos_fmt["pago_real"] / 1e6).round(2)
    eventos_fmt["desvio_padronizado"] = eventos_fmt["desvio_padronizado"].round(2)
    tabela_eventos = eventos_fmt[["orgao", "tipo_instituicao", "ano", "pago_real_mi",
                                   "desvio_padronizado", "n_anos_serie"]]
    tabela_eventos["orgao"] = tabela_eventos["orgao"].str.slice(0, 60)

    # Comparação com flag_salto_anual: quantos dos eventos Theil-Sen também
    # foram sinalizados por flag_salto_anual no mesmo ano/série?
    referencia = df[["chave_serie", "ano", "flag_salto_anual"]]
    comparacao = eventos_limitados.merge(referencia, on=["chave_serie", "ano"], how="left")
    n_tambem_salto = int(comparacao["flag_salto_anual"].fillna(False).sum())
    pct_tambem_salto = f"{n_tambem_salto / len(eventos_limitados):.0%}" if len(eventos_limitados) else "n/d"

    caminho_grafico = grafico_exemplos(df, eventos_limitados)
    grafico_md = f"![Exemplos de eventos]({Path(caminho_grafico).relative_to(DIR_RELATORIOS)})" if caminho_grafico else "_Sem eventos para ilustrar._"

    linhas = f"""# Séries temporais por instituição — tarefa 2.4

Gerado por `analises/05_series.py`. Base: Conjunto B (`despesas_por_instituicao_v2`),
excluindo ano parcial. {n_series_elegiveis} instituições têm ≥{MIN_ANOS} anos
elegíveis (critério do ROADMAP) e entraram na análise. Método: tendência
robusta de Theil–Sen sobre `pago_real` por instituição; resíduo
padronizado pelo desvio robusto (MAD × 1,4826) dos próprios resíduos;
eventos = |resíduo padronizado| > {LIMIAR_DESVIO}.

## 1. Eventos detectados

{len(eventos)} eventos no total (mostrando até {MAX_EVENTOS}, ordenados por
desvio absoluto).

{tabela_md(tabela_eventos)}

## 2. Exemplos ilustrados

{grafico_md}

**Leitura dos gráficos:** linha sólida com marcadores é o valor real
observado; linha tracejada é a tendência de Theil–Sen (mediana das
inclinações entre todos os pares de anos — pouco sensível ao próprio
evento que está sendo detectado); "×" marca os anos sinalizados como
evento.

## 3. Comparação com `flag_salto_anual` (Fase 1)

Dos {len(eventos_limitados)} eventos listados acima, apenas {n_tambem_salto}
também têm `flag_salto_anual=True` no mesmo ano/instituição ({pct_tambem_salto}) —
sobreposição muito baixa, achado a registrar: os dois critérios praticamente
não se substituem, cada um captura uma fatia diferente dos casos, e nenhum
dos dois é redundante em relação ao outro para fins de priorização.
Os dois métodos capturam fenômenos relacionados mas não idênticos:
`flag_salto_anual` compara cada ano só com o ano anterior (sensível a
mudanças abruptas de curto prazo, mesmo que a série volte ao patamar
seguinte); o resíduo de Theil–Sen compara cada ano com a tendência de
**toda a série** (sensível a um ano fora do padrão de longo prazo, mesmo
que a variação ano a ano não pareça extrema isoladamente — ex.: um platô
alto de 3 anos seguido de volta ao normal pode não gerar
`flag_salto_anual` em nenhum ano individual, mas gera resíduo alto nos 3
anos do platô). Eventos capturados por só um dos dois métodos não são
menos importantes — são complementares.

## 4. Padrão já conhecido vs. achados novos

Quatro das instituições no topo da lista (Cariri, Oeste da Bahia, Sul da
Bahia, Sul e Sudeste do Pará, todas com evento em 2014, ocasionalmente
também 2015) são as universidades federais criadas na expansão de
2013–2014, já identificadas em `relatorios/02_eda.md` (seção 6) e
`relatorios/04_outliers.md` (seção 3): com 12 anos de histórico completo
hoje, elas passam no critério de ≥{MIN_ANOS} anos, mas o primeiro ano
(orçamento de implantação, uma fração do valor maduro) inevitavelmente
aparece como resíduo extremo em relação à tendência de 12 anos — efeito
estrutural conhecido, não achado novo.

Os demais eventos **não têm explicação estrutural identificada nos dados
já analisados** e são achados desta tarefa: destacam-se padrões de
oscilação em instituições já consolidadas (não recém-criadas), como
Universidade Federal Rural do Rio de Janeiro (queda sustentada 2019→2021,
recuperação parcial depois) e Fundação Universidade Federal do Vale do São
Francisco (queda até 2021, salto acentuado em 2024–2025) — ver painéis 2 e
4 da figura acima. Esses casos são prioridade para a consolidação da
tarefa 2.5.

## 5. Limitações

- Resultados desta tarefa alimentam a consolidação de casos da tarefa 2.5,
  junto com EDA (2.1), Benford (2.2) e outliers multivariados (2.3).
- Theil–Sen usa só o par (ano, valor) — não considera taxa de execução,
  porte da instituição ou contexto orçamentário; um resíduo alto é
  candidato a checagem manual, não conclusão sobre a causa.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    df = carregar()

    n_series_elegiveis = int((df.groupby("chave_serie")["ano"].nunique() >= MIN_ANOS).sum())
    eventos = detectar_eventos_serie(
        df, chave="chave_serie", coluna_valor="pago_real", min_anos=MIN_ANOS, limiar_desvio=LIMIAR_DESVIO
    )

    eventos_salvos = eventos.head(MAX_EVENTOS).merge(
        df[["chave_serie", "orgao", "tipo_instituicao"]].drop_duplicates(), on="chave_serie", how="left"
    )
    caminho_csv = DIR_DADOS / "eventos_series.csv"
    eventos_salvos.to_csv(caminho_csv, index=False, encoding="utf-8")
    print(f"Salvo: {caminho_csv} ({len(eventos_salvos)} eventos)")

    conteudo = gerar_relatorio(df, eventos, n_series_elegiveis)
    caminho_md = DIR_RELATORIOS / "05_series.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
