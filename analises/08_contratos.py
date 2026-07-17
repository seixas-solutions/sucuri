#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.2 do ROADMAP — Contratos das instituições.

Coleta `/contratos` para uma amostra estratificada de 15 instituições do
Conjunto B (3 maiores, 3 medianas e 3 menores universidades federais; 3
institutos federais; EBSERH; CAPES; 1 hospital universitário adicional),
2023–2025 (não 2018+ como sugerido no ROADMAP: um teste de paginação
mostrou só a UFRJ tendo 450+ contratos em 2018–2025 — cobrir isso para 15
órgãos custaria centenas de requisições; 2023–2025 é uma amostra real,
mas deliberadamente mais estreita — ver seção de limitações do relatório).

Calcula por contrato: valor aditivado (`valorFinalCompra -
valorInicialCompra`), prazo em dias, se a modalidade é
dispensa/inexigibilidade; por órgão: índice Herfindahl de concentração de
fornecedores.

Uso:
    uv run python analises/08_contratos.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.contratos import coletar_contratos_orgao, construir_df_contratos, indice_herfindahl

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DATA_INICIO = date(2023, 1, 1)
DATA_FIM = date(2025, 12, 31)

INSTITUICOES_PILOTO = [
    ("26245", "Universidade Federal do Rio de Janeiro"),
    ("26238", "Universidade Federal de Minas Gerais"),
    ("26236", "Universidade Federal Fluminense"),
    ("26273", "Universidade Federal do Rio Grande"),
    ("26269", "Universidade Federal do Estado do Rio de Janeiro"),
    ("26254", "Universidade Federal do Triângulo Mineiro"),
    ("26454", "Universidade Federal de Rondonópolis"),
    ("26455", "Universidade Federal do Delta do Parnaíba"),
    ("26456", "Universidade Federal do Agreste de Pernambuco"),
    ("26439", "Instituto Federal de Educação, Ciência e Tecnologia de São Paulo"),
    ("26405", "Instituto Federal de Educação, Ciência e Tecnologia do Ceará"),
    ("26408", "Instituto Federal de Educação, Ciência e Tecnologia do Maranhão"),
    ("26443", "Empresa Brasileira de Serviços Hospitalares"),
    ("26291", "Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior"),
    ("26294", "Hospital de Clínicas de Porto Alegre"),
]


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def coletar_tudo(sessao) -> list[dict]:
    todos: list[dict] = []
    for codigo_orgao, nome in INSTITUICOES_PILOTO:
        registros = coletar_contratos_orgao(sessao, codigo_orgao, DATA_INICIO, DATA_FIM)
        print(f"  {nome} ({codigo_orgao}): {len(registros)} contratos")
        todos.extend(registros)
    return todos


def gerar_relatorio(df: pd.DataFrame, n_brutos: int) -> str:
    if df.empty:
        return "# Contratos das instituições — tarefa 3.2\n\nNenhum contrato coletado.\n"

    hhi = indice_herfindahl(df).sort_values("hhi_fornecedores", ascending=False)
    nomes = dict(INSTITUICOES_PILOTO)
    hhi["orgao"] = hhi["codigoOrgao"].map(nomes)
    decil_corte = hhi["hhi_fornecedores"].quantile(0.9)
    decil_superior = hhi[hhi["hhi_fornecedores"] >= decil_corte]

    hhi_fmt = hhi.copy()
    hhi_fmt["hhi_fornecedores"] = hhi_fmt["hhi_fornecedores"].round(0)
    tabela_hhi = hhi_fmt[["orgao", "codigoOrgao", "n_fornecedores", "hhi_fornecedores"]].to_markdown(index=False)

    n_dispensa = int(df["eh_dispensa_ou_inexigibilidade"].sum())
    pct_dispensa = n_dispensa / len(df)

    aditivados = df[df["valor_aditivado"] > 0]
    resumo_aditivos = (
        f"{len(aditivados)} de {len(df)} contratos ({len(aditivados)/len(df):.1%}) tiveram valor final "
        f"maior que o inicial; aditivo médio nesses casos: {fmt_brl(aditivados['valor_aditivado'].mean())} "
        f"({aditivados['pct_aditivado'].mean():.1%} do valor inicial, em média)."
        if len(aditivados) else "Nenhum contrato com valor final maior que o inicial nesta amostra."
    )

    linhas = f"""# Contratos das instituições — tarefa 3.2

Gerado por `analises/08_contratos.py`. Amostra: {len(INSTITUICOES_PILOTO)}
instituições do Conjunto B (estratificada por porte/tipo — ver script),
contratos vigentes entre {DATA_INICIO:%d/%m/%Y} e {DATA_FIM:%d/%m/%Y}.
{n_brutos} contratos brutos coletados.

## 1. Limitação de escopo desta tarefa

O ROADMAP original sugeria "anos 2018+"; um teste de paginação mostrou só
a UFRJ tendo 450+ contratos nesse intervalo — cobrir isso para uma amostra
de 15 órgãos custaria centenas de requisições. Optou-se por
{DATA_INICIO:%Y}–{DATA_FIM:%Y} (3 anos), amostra real e válida para a
análise de concentração de fornecedores, mas não o histórico completo.
Coleta mais longa (2018+, mais órgãos) fica para o usuário rodar
externamente — ver EXTERNAL.md.

## 2. Concentração de fornecedores (índice Herfindahl-Hirschman)

Escala 0–10.000 (soma dos market-shares percentuais ao quadrado, por
valor final de contrato). Referência de literatura antitruste: >2.500 é
convencionalmente "altamente concentrado" — usado aqui só como escala de
leitura, não como acusação (poucos fornecedores pode refletir mercado
naturalmente concentrado para o objeto contratado, ex.: obra
especializada).

{tabela_hhi}

### Decil superior de concentração ({len(decil_superior)} de {len(hhi)} instituições, HHI ≥ {decil_corte:.0f})

{decil_superior[["orgao", "codigoOrgao", "n_fornecedores", "hhi_fornecedores"]].to_markdown(index=False)}

**Leitura do 1º colocado (UFF, HHI 7.512 apesar de 87 fornecedores
distintos):** o HHI pondera por valor, não por contagem — um único
fornecedor, a "Fundação Euclides da Cunha de Apoio Institucional à UFF",
concentra R$ 403,9 milhões dos R$ 466,5 milhões em contratos da UFF no
período (86,6%). Isso não é um fornecedor comercial comum: fundações de
apoio são entidades sem fins lucrativos que administram projetos de
pesquisa/extensão em nome da universidade — um arranjo comum e legal em
universidades federais brasileiras, não um indício automático de
irregularidade. Ainda assim, fundações de apoio já foram objeto de
apontamentos de auditoria do TCU em outras instituições por concentração
de contratação sem licitação — vale conferir a tarefa 3.3 (licitações) e,
na Fase 4, achados públicos do TCU/CGU especificamente sobre essa
fundação, antes de qualquer conclusão.

**Nota sobre instituição sem contratos nesta amostra:** Hospital de
Clínicas de Porto Alegre (`codigoOrgao=26294`, confirmado válido via
`/orgaos-siafi`) retornou 0 contratos em 2023–2025 — não investigado
nesta tarefa se é ausência real de contratos nesse período, publicação
sob outro código/canal (HCPA é sociedade de economia mista, regime de
contratação potencialmente distinto de universidades federais), ou
lacuna de dados. Fica como item em aberto, não como conclusão.

## 3. Dispensa e inexigibilidade de licitação

{n_dispensa} de {len(df)} contratos ({pct_dispensa:.1%}) foram
contratados por dispensa ou inexigibilidade de licitação (identificado
pelo texto de `modalidadeCompra`) — modalidades legais, mas que dispensam
concorrência; proporção alta num órgão específico é sinal a cruzar com a
tarefa 3.3 (licitações) antes de qualquer leitura.

## 4. Termos aditivos

{resumo_aditivos}

## 5. Dados salvos

`dados/contratos_mec.parquet` — um registro por contrato, com as colunas
derivadas (`valor_aditivado`, `pct_aditivado`, `prazo_dias`,
`eh_dispensa_ou_inexigibilidade`). Usado na tarefa 3.4 para cruzar
fornecedores com sanções (CEIS/CNEP).
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    print("Coletando contratos...")
    registros = coletar_tudo(sessao)

    caminho_raw = DIR_DADOS / "raw" / "contratos_mec_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df = construir_df_contratos(registros)
    if not df.empty:
        df.to_parquet(DIR_DADOS / "contratos_mec.parquet", index=False)
        print(f"Salvo: dados/contratos_mec.parquet ({len(df)} linhas)")

    conteudo = gerar_relatorio(df, len(registros))
    caminho_md = DIR_RELATORIOS / "08_contratos.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
