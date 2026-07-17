#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.4 do ROADMAP — Sanções: CEIS, CNEP e acordos de leniência.

CEIS/CNEP/acordos-leniência filtram por CNPJ, não por órgão, e são
registros nacionais grandes (CEIS sozinho tem mais de 12 mil páginas de 15
registros — confirmado empiricamente; baixar tudo é impraticável aqui).
Em vez disso, consulta-se **um CNPJ de cada vez**, usando como lista de
entrada os fornecedores que já respondem por 80% do valor total
contratado em `dados/contratos_mec.parquet` (tarefa 3.2) — prioriza onde
está o dinheiro, não uma amostra aleatória.

Uso:
    uv run python analises/10_sancoes.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.sancoes import construir_df_sancoes, consultar_sancoes_lista_cnpjs, cruzar_contratos_sancionados

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
COBERTURA_VALOR_ALVO = 0.80


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def selecionar_fornecedores(df_contratos: pd.DataFrame, cobertura: float = COBERTURA_VALOR_ALVO) -> list[str]:
    por_fornecedor = (
        df_contratos[df_contratos["fornecedorCnpjCpf"].str.strip().ne("")]
        .groupby("fornecedorCnpjCpf")["valorFinalCompra"].sum()
        .sort_values(ascending=False)
    )
    acumulado = por_fornecedor.cumsum() / por_fornecedor.sum()
    n = int((acumulado <= cobertura).sum()) + 1
    return por_fornecedor.head(n).index.tolist()


def gerar_relatorio(
    df_contratos: pd.DataFrame, df_sancoes: pd.DataFrame, cruzamento: pd.DataFrame,
    n_cnpjs_consultados: int, n_registros_brutos: int
) -> str:
    if df_sancoes.empty:
        resumo_sancoes_md = "_Nenhum dos CNPJs consultados tem registro em CEIS/CNEP/acordos de leniência._"
    else:
        resumo = df_sancoes.groupby("fonte").size().reset_index(name="n_registros")
        resumo_sancoes_md = resumo.to_markdown(index=False)

    n_cnpjs_com_sancao_e_contrato = 0
    n_cruzamento_bruto = 0
    if not df_sancoes.empty:
        bruto = df_contratos.merge(df_sancoes, left_on="fornecedorCnpjCpf", right_on="cnpjSancionado", how="inner")
        n_cruzamento_bruto = len(bruto)
        n_cnpjs_com_sancao_e_contrato = bruto["fornecedorCnpjCpf"].nunique()

    if cruzamento.empty:
        nota_zero = ""
        if n_cruzamento_bruto:
            nota_zero = (
                f"\n\n**Achado desta tarefa:** {n_cnpjs_com_sancao_e_contrato} CNPJs entre os "
                f"consultados têm sanção registrada E contrato no período coletado "
                f"({n_cruzamento_bruto} combinações contrato×sanção no total) — mas em "
                f"**nenhuma** delas a sanção começou antes ou durante a vigência da assinatura "
                f"do contrato correspondente; todas as sanções encontradas começaram depois do "
                f"contrato já assinado. Reportar só o número bruto ({n_cruzamento_bruto}) sem "
                f"o filtro de data teria sido enganoso — pareceria um sinal forte quando, com a "
                f"cronologia correta, não há nenhum caso de contratação com fornecedor já "
                f"sancionado nesta amostra."
            )
        cruzamento_md = "_Nenhum contrato assinado com fornecedor já sancionado na data da assinatura._" + nota_zero
    else:
        cols = ["orgao", "fornecedorNome", "dataAssinatura", "dataInicioSancao", "dataFimSancao",
                "fonte", "valorFinalCompra"]
        cols = [c for c in cols if c in cruzamento.columns]
        cruzamento_fmt = cruzamento[cols].copy()
        if "valorFinalCompra" in cruzamento_fmt.columns:
            cruzamento_fmt["valorFinalCompra"] = cruzamento_fmt["valorFinalCompra"].map(fmt_brl)
        cruzamento_md = cruzamento_fmt.to_markdown(index=False, disable_numparse=True)

    linhas = f"""# Sanções: CEIS, CNEP e acordos de leniência — tarefa 3.4

Gerado por `analises/10_sancoes.py`. {n_cnpjs_consultados} CNPJs de
fornecedores consultados (os que somam {COBERTURA_VALOR_ALVO:.0%} do valor
total contratado em `dados/contratos_mec.parquet`) × 3 fontes (CEIS, CNEP,
acordos de leniência) = até {n_cnpjs_consultados * 3} requisições.
{n_registros_brutos} registros de sanção brutos encontrados (antes de
qualquer filtro).

## 1. Por que consulta direcionada, não a base completa

CEIS, CNEP e acordos de leniência são registros **nacionais**, não
filtráveis por órgão — abrangem todo o setor público, não só o MEC. Uma
sondagem de paginação encontrou o CEIS ainda com páginas cheias na página
800 (12.000+ registros só nesse cadastro) — baixar a base inteira para
depois cruzar seria uma coleta de escala muito maior que este piloto.
Consultar por CNPJ direcionado é mais barato E mais preciso: só interessam
sanções de empresas que **já são fornecedoras do MEC**, e essas já estão
listadas em `contratos_mec.parquet`.

## 2. Sanções encontradas entre os fornecedores consultados

{resumo_sancoes_md}

## 3. Contratos assinados com fornecedor já sancionado na data da assinatura

Cruzamento: fornecedor do contrato aparece em CEIS/CNEP/acordos de
leniência **com o período de sanção cobrindo a data de assinatura do
contrato** (não apenas "tem alguma sanção em algum momento" — sanção
posterior ao contrato não é o mesmo sinal).

{cruzamento_md}

## 4. Dados salvos

`dados/sancoes.parquet` — todos os registros de sanção encontrados (não só
os cruzados com contratos). `dados/contratos_com_sancionados.csv` — o
cruzamento da seção 3 (pode estar vazio; o cruzamento roda de qualquer
forma, como pede o ROADMAP).

## 5. Limitação de escopo

Cobertura de {COBERTURA_VALOR_ALVO:.0%} do valor contratado deixa de fora
fornecedores de contratos pequenos (que, individualmente, pesam pouco no
valor total, mas cuja ausência de checagem não deve ser lida como "sem
sanção" — apenas "não verificado nesta amostra"). Verificar os
{"" if n_cnpjs_consultados == 0 else "demais"} fornecedores fica para o
usuário rodar externamente (ver EXTERNAL.md).
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    df_contratos = pd.read_parquet(DIR_DADOS / "contratos_mec.parquet")
    cnpjs = selecionar_fornecedores(df_contratos)
    print(f"Consultando sanções para {len(cnpjs)} CNPJs (80% do valor contratado)...")

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)
    registros = consultar_sancoes_lista_cnpjs(sessao, cnpjs)

    caminho_raw = DIR_DADOS / "raw" / "sancoes_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df_sancoes = construir_df_sancoes(registros)
    if not df_sancoes.empty:
        df_sancoes.to_parquet(DIR_DADOS / "sancoes.parquet", index=False)
    print(f"Salvo: dados/sancoes.parquet ({len(df_sancoes)} linhas)")

    cruzamento = cruzar_contratos_sancionados(df_contratos, df_sancoes)
    cruzamento.to_csv(DIR_DADOS / "contratos_com_sancionados.csv", index=False, encoding="utf-8")
    print(f"Salvo: dados/contratos_com_sancionados.csv ({len(cruzamento)} linhas)")

    conteudo = gerar_relatorio(df_contratos, df_sancoes, cruzamento, len(cnpjs), len(registros))
    caminho_md = DIR_RELATORIOS / "10_sancoes.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
