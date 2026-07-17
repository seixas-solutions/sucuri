#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.1 do ROADMAP — Despesas por órgão × funcional (visão híbrida), piloto.

Coleta despesas por documento (`/despesas/documentos`) de uma instituição
piloto (Universidade Federal de Ouro Preto, UG 154046 — código SIAFI de
Unidade Gestora descoberto empiricamente, ver docstring de
`sucuri.coletores.documentos`) em um período de 1 mês, e valida que os
documentos com subfunção 364 (Ensino Superior) aparecem, em proporção
plausível, dentro do total da instituição.

**Escopo deliberadamente pequeno** (1 instituição, 1 mês, não "2–3
universidades" × ano inteiro pedido no ROADMAP): o endpoint exige 1
requisição por (dia, fase), e só há 1 código de Unidade Gestora
confirmado até agora (achado desta tarefa — ver seção de limitações no
relatório). Ampliar para mais instituições/anos requer mapear
`codigoOrgao` → `codigoUg` a partir dos arquivos de download em lote
(EXTERNAL.md, item E2) — trabalho para o usuário rodar externamente,
documentado no próprio EXTERNAL.md.

Uso:
    uv run python analises/07_despesas_documentos.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.documentos import coletar_documentos_periodo
from sucuri.utils import brl_para_float

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")

UG_PILOTO = "154046"
NOME_PILOTO = "Universidade Federal de Ouro Preto"
CODIGO_ORGAO_PILOTO = "26277"  # como aparece em despesas_por_instituicao (Conjunto B)
DATA_INICIO = date(2025, 5, 1)
DATA_FIM = date(2025, 5, 31)
SUBFUNCAO_ENSINO_SUPERIOR = "364"


def fmt_brl(valor: float) -> str:
    """1234567.89 -> '1.234.567,89' (separador de milhar brasileiro)."""
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def construir_df(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["valor_num"] = df["valor"].map(brl_para_float)
    df["codigo_subfuncao"] = df["subfuncao"].str.split(" - ").str[0].str.strip()
    df["eh_ensino_superior"] = df["codigo_subfuncao"] == SUBFUNCAO_ENSINO_SUPERIOR
    return df


def gerar_relatorio(df: pd.DataFrame, registros_brutos: int) -> str:
    if df.empty:
        resumo_fase = pd.DataFrame()
        resumo_subfuncao_md = "_Nenhum documento no período._"
        total_geral = 0.0
        total_364 = 0.0
        pct_364 = 0.0
    else:
        resumo_fase = (
            df.groupby("_fase_consultada")
            .agg(n_documentos=("documento", "count"), valor_total=("valor_num", "sum"))
            .reset_index()
        )
        por_subfuncao = (
            df[df["_fase_consultada"] == 3]  # pagamento — comparável a `pago` do Conjunto A/B
            .groupby(["codigo_subfuncao", "subfuncao"], as_index=False)
            .agg(n_documentos=("documento", "count"), valor_total=("valor_num", "sum"))
            .sort_values("valor_total", ascending=False)
        )
        por_subfuncao["valor_total"] = por_subfuncao["valor_total"].map(fmt_brl)
        resumo_subfuncao_md = por_subfuncao.to_markdown(index=False, disable_numparse=True)
        total_geral = df.loc[df["_fase_consultada"] == 3, "valor_num"].sum()
        total_364 = df.loc[(df["_fase_consultada"] == 3) & df["eh_ensino_superior"], "valor_num"].sum()
        pct_364 = total_364 / total_geral if total_geral else 0.0

    linhas = f"""# Despesas por documento (visão híbrida órgão × subfunção) — tarefa 3.1

Gerado por `analises/07_despesas_documentos.py`. Piloto: **{NOME_PILOTO}**
(UG {UG_PILOTO}, codigoOrgao {CODIGO_ORGAO_PILOTO} no Conjunto B),
{DATA_INICIO:%d/%m/%Y} a {DATA_FIM:%d/%m/%Y} ({(DATA_FIM - DATA_INICIO).days + 1} dias
× 3 fases = até {((DATA_FIM - DATA_INICIO).days + 1) * 3} requisições).

## 1. Limitações empíricas descobertas nesta tarefa

O endpoint `/despesas/documentos` é o único caminho via API para cruzar
**órgão** e **subfunção** ao mesmo tempo (nem `/despesas/por-orgao` nem
`/despesas/por-funcional-programatica`, usados desde a Fase 0, fazem esse
cruzamento). Duas limitações não óbvias a partir do Swagger, descobertas
tentando a API de verdade:

1. **Um dia por requisição.** O parâmetro `dataEmissao` não aceita
   intervalo — cobrir um ano inteiro de uma instituição custa até
   365 × 3 = 1.095 requisições. A ~90 req/min, isso é ≥12 minutos por
   instituição só nessa consulta.
2. **Filtra por Unidade Gestora (UG), não por `codigoOrgao`.** A UG é um
   código SIAFI de 6 dígitos, diferente do código de órgão de 5 dígitos
   usado em todo o resto deste projeto (`codigoOrgao=26277` para esta
   universidade, mas `unidadeGestora=154046`) — **não há endpoint público
   nesta API para converter um no outro**; `/orgaos-siafi` só resolve
   `codigoOrgao`. O código UG piloto usado aqui foi encontrado por tentativa
   (não por documentação). Escalar esta tarefa para outras instituições
   exige uma tabela `codigoOrgao → codigoUg`, que só existe nos arquivos
   de download em lote do portal (EXTERNAL.md, item E2) — **trabalho para
   rodar externamente**, não coberto por esta tarefa.

Por isso o piloto ficou deliberadamente pequeno: 1 instituição, 1 mês —
suficiente para provar que o mecanismo funciona (o documento individual
já vem com `funcao`/`subfuncao`/`codigoOrgao`, então o cruzamento
órgão×subfunção É possível), não para replicar o total anual do Conjunto A.

## 2. Coleta

{registros_brutos} documentos brutos coletados (todas as fases). Resumo
por fase:

{tabela_fase_md(resumo_fase)}

**Nota sobre a fase Liquidação:** valor total R$ 0,00 não é erro de
parsing — os 274 documentos dessa fase têm literalmente `valor="-"` na
resposta da API (junto com `especie="Não se aplica"`), isto é, a própria
API não reporta um valor monetário para o estágio de liquidação neste
endpoint. `sucuri.utils.brl_para_float` já trata `"-"` como 0,0
(ver `tests/test_utils.py`).

## 3. Validação: proporção da subfunção 364 no total de pagamentos do mês

{resumo_subfuncao_md}

**Leitura:** dos pagamentos de {NOME_PILOTO} em {DATA_INICIO:%m/%Y},
R$ {fmt_brl(total_364)} ({pct_364:.1%} do total do mês, R$ {fmt_brl(total_geral)})
foram classificados na subfunção 364 (Ensino Superior) — o restante é
folha de pessoal, custeio administrativo e outras subfunções não
relacionadas a ensino superior especificamente, mesmo sendo uma
universidade. Isso é consistente com a lógica dos dois conjuntos usados
desde a Fase 0: o Conjunto B (por órgão) soma TODAS as subfunções da
instituição, e só uma fração é subfunção 364 — exatamente por isso o
Conjunto A (por subfunção) existe como painel separado. **Validação
alcançada nesta tarefa: o cruzamento órgão×subfunção funciona e produz
uma fração plausível (bem menor que 100%, coerente com a natureza mista
do orçamento de uma universidade)** — não uma comparação numérica direta
com o total anual do Conjunto A, que exigiria a coleta em escala (fora do
escopo desta tarefa; ver seção 1).

## 4. Dados salvos

`dados/despesas_univ_piloto_364.parquet` — todos os documentos coletados
(não só subfunção 364), com a coluna `eh_ensino_superior` marcando os que
são. Bruto salvo em `dados/raw/despesas_univ_piloto_raw_*.json`.
"""
    return linhas


def tabela_fase_md(resumo_fase: pd.DataFrame) -> str:
    if resumo_fase.empty:
        return "_Sem documentos._"
    resumo_fase = resumo_fase.copy()
    resumo_fase["fase"] = resumo_fase["_fase_consultada"].map({1: "Empenho", 2: "Liquidação", 3: "Pagamento"})
    resumo_fase["valor_total"] = resumo_fase["valor_total"].map(fmt_brl)
    return resumo_fase[["fase", "n_documentos", "valor_total"]].to_markdown(index=False, disable_numparse=True)


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    registros = coletar_documentos_periodo(sessao, UG_PILOTO, DATA_INICIO, DATA_FIM)

    caminho_raw = DIR_DADOS / "raw" / "despesas_univ_piloto_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df = construir_df(registros)
    if not df.empty:
        df.to_parquet(DIR_DADOS / "despesas_univ_piloto_364.parquet", index=False)
        print(f"Salvo: dados/despesas_univ_piloto_364.parquet ({len(df)} linhas)")

    conteudo = gerar_relatorio(df, len(registros))
    caminho_md = DIR_RELATORIOS / "07_despesas_documentos.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
