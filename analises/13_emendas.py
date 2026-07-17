#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.7 do ROADMAP — Emendas parlamentares destinadas ao ensino superior.

Coleta `/emendas` filtrado por função 12 (Educação) + subfunção 364
(Ensino Superior), 2014–2025 (mesmo intervalo do Conjunto A), e compara o
total anual de emendas com o total anual do Conjunto A (`pago_real`) —
"dependência de emendas" como % do orçamento da subfunção, no nível
agregado nacional. Também marca anos eleitorais (municipais e gerais) para
checar saltos.

**Escopo menor que o pedido no ROADMAP** ("beneficiários que são órgãos do
Conjunto B"): nem `/emendas` nem `/emendas/documentos/{codigo}` expõem a
instituição beneficiária — só UF (`localidadeDoGasto`) ou um código de
documento prefixado por Unidade Gestora sem mapeamento público (mesmo
problema da tarefa 3.1). A análise por instituição específica não é
possível com os dados desta API sozinha — ver seção de limitações do
relatório.

Uso:
    uv run python analises/13_emendas.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.emendas import coletar_emendas_intervalo, construir_df_emendas, marcar_ano_eleitoral

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
ANO_INICIO = 2014
ANO_FIM = 2025


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def gerar_relatorio(df_emendas: pd.DataFrame, df_a: pd.DataFrame, n_brutos: int) -> str:
    if df_emendas.empty:
        return "# Emendas parlamentares — tarefa 3.7\n\nNenhuma emenda coletada.\n"

    df_emendas = marcar_ano_eleitoral(df_emendas)
    por_ano_emendas = df_emendas.groupby("ano")["valorPago"].sum().rename("emendas_pago")

    total_a_por_ano = df_a[~df_a["ano_parcial"]].groupby("ano")["pago_real"].sum().rename("subfuncao364_pago_real")

    serie = pd.concat([por_ano_emendas, total_a_por_ano], axis=1).dropna()
    serie["pct_dependencia"] = serie["emendas_pago"] / serie["subfuncao364_pago_real"]
    serie = serie.reset_index()
    anos_eleitorais_geral_municipal = {2014, 2016, 2018, 2020, 2022, 2024}
    serie["ano_eleitoral"] = serie["ano"].isin(anos_eleitorais_geral_municipal)

    serie_fmt = serie.copy()
    serie_fmt["emendas_pago"] = serie_fmt["emendas_pago"].map(fmt_brl)
    serie_fmt["subfuncao364_pago_real"] = serie_fmt["subfuncao364_pago_real"].map(fmt_brl)
    serie_fmt["pct_dependencia"] = serie_fmt["pct_dependencia"].map(lambda v: f"{v:.2%}")
    serie_md = serie_fmt.to_markdown(index=False, disable_numparse=True)

    media_eleitoral = serie.loc[serie["ano_eleitoral"], "pct_dependencia"].mean()
    media_nao_eleitoral = serie.loc[~serie["ano_eleitoral"], "pct_dependencia"].mean()

    top_autores = (
        df_emendas.groupby("autor")["valorPago"].sum().sort_values(ascending=False).head(10)
    )
    top_autores_md = top_autores.reset_index().rename(columns={"valorPago": "valor_total"})
    top_autores_md["valor_total"] = top_autores_md["valor_total"].map(fmt_brl)
    top_autores_md = top_autores_md.to_markdown(index=False, disable_numparse=True)

    linhas = f"""# Emendas parlamentares destinadas ao ensino superior — tarefa 3.7

Gerado por `analises/13_emendas.py`. {n_brutos} emendas brutas coletadas
(função Educação, subfunção Ensino Superior, {ANO_INICIO}–{ANO_FIM}).

## 1. Limitação de escopo desta tarefa

O ROADMAP pedia cruzar emendas com "beneficiários que são órgãos do
Conjunto B" — não é possível com os dados desta API: nem `/emendas` nem
`/emendas/documentos/{{codigo}}` expõem a instituição beneficiária.
`/emendas` só tem `localidadeDoGasto` em nível de **UF**, não de órgão;
`/emendas/documentos/{{codigo}}` só tem um código de documento prefixado
por Unidade Gestora (ex.: `151910264182023NE000080`) — sem endpoint
público para converter UG em `codigoOrgao`, o mesmo obstáculo já
encontrado e documentado na tarefa 3.1. A análise abaixo é no nível
**agregado nacional da subfunção 364**, comparável ao Conjunto A, não por
instituição.

## 2. Dependência de emendas como % do orçamento (subfunção 364, nacional)

{serie_md}

**Leitura:** emendas pagas / total pago (real) da subfunção 364 no
Conjunto A, por ano. Valores em R$ reais (ano-base 2025 — mesma
deflação da Fase 1). Em termos absolutos, emendas são uma fração muito
pequena do orçamento de ensino superior (mediana ~0,2% no período) —
consistente com o achado da tarefa 2.1 de que a subfunção 364 é
majoritariamente folha de pagamento, não algo financiável por emenda
parlamentar. Ainda assim, há uma tendência real de **crescimento
relativo**: de 0,01–0,04% em 2014–2017 para 0,3–0,7% a partir de 2020 —
um salto de ordem de grandeza, não ruído. O ano de maior valor absoluto
(2023, R$ 264,3 milhões) e o 2º maior autor agregado ("RELATOR GERAL",
R$ 74,0 milhões no período) são consistentes com a mudança nas regras de
emendas parlamentares no Brasil nesse intervalo (emendas individuais e de
bancada tornadas impositivas por emenda constitucional a partir de 2015;
emendas de relator geral — o chamado "orçamento secreto" — ganharam peso
em 2020–2022 até serem objeto da ADPF 850 no STF, dezembro/2022, e o
desenho de emendas ser reformulado a partir de 2023) — contexto público
já bem documentado, não uma interpretação exclusiva desta análise.

## 3. Anos eleitorais vs. não eleitorais

Dependência média de emendas em anos eleitorais (municipais e gerais):
{media_eleitoral:.2%}. Em anos não eleitorais: {media_nao_eleitoral:.2%}.
{"Maior em anos eleitorais, consistente com a hipótese do ROADMAP." if pd.notna(media_eleitoral) and pd.notna(media_nao_eleitoral) and media_eleitoral > media_nao_eleitoral else "Sem diferença clara na direção esperada nesta amostra — não confirma a hipótese de saltos ligados a anos eleitorais."}

## 4. Top 10 autores por valor total de emendas (todo o período)

{top_autores_md}

## 5. Dados salvos

`dados/emendas_educacao.parquet` — uma linha por emenda/ano coletada
(agregado por autor/localidade, não por documento individual).
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    print("Coletando emendas...")
    registros = coletar_emendas_intervalo(sessao, ANO_INICIO, ANO_FIM)

    caminho_raw = DIR_DADOS / "raw" / "emendas_educacao_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df_emendas = construir_df_emendas(registros)
    if not df_emendas.empty:
        df_emendas.to_parquet(DIR_DADOS / "emendas_educacao.parquet", index=False)
        print(f"Salvo: dados/emendas_educacao.parquet ({len(df_emendas)} linhas)")

    df_a = pd.read_parquet(DIR_DADOS / "despesas_ensino_superior_v2.parquet")

    conteudo = gerar_relatorio(df_emendas, df_a, len(registros))
    caminho_md = DIR_RELATORIOS / "13_emendas.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
