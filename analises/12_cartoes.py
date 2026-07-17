#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.6 do ROADMAP — Cartão de Pagamento do Governo Federal (CPGF).

Coleta `/cartoes` (CPGF, tipoCartao=1) para as mesmas 15 instituições
piloto das tarefas 3.2/3.3, 2023–2025. Aplica as regras de red flag do
ROADMAP: gastos por portador, transações em fim de semana/dezembro,
prováveis saques (heurística — ver `sucuri.coletores.cartoes`), valores
repetidos pelo mesmo portador.

Uso:
    uv run python analises/12_cartoes.py
"""

from __future__ import annotations

import json
from pathlib import Path

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.cartoes import (
    coletar_cartoes,
    construir_df_cartoes,
    resumo_red_flags_por_orgao,
    valores_repetidos_mesmo_portador,
)

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
ANO_INICIO = 2023
ANO_FIM = 2025

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
        registros = coletar_cartoes(sessao, codigo_orgao, ANO_INICIO, ANO_FIM)
        print(f"  {nome} ({codigo_orgao}): {len(registros)} transações")
        todos.extend(registros)
    return todos


def gerar_relatorio(df, n_brutos: int) -> str:
    if df.empty:
        return "# Cartão de Pagamento do Governo Federal (CPGF) — tarefa 3.6\n\nNenhuma transação coletada.\n"

    resumo = resumo_red_flags_por_orgao(df)
    resumo_fmt = resumo.copy()
    resumo_fmt["valor_total"] = resumo_fmt["valor_total"].map(fmt_brl)
    resumo_fmt["pct_fim_de_semana"] = resumo_fmt["pct_fim_de_semana"].map(lambda v: f"{v:.1%}")
    resumo_fmt["pct_provavel_saque"] = resumo_fmt["pct_provavel_saque"].map(lambda v: f"{v:.1%}")
    resumo_md = resumo_fmt[[
        "orgao", "n_transacoes", "valor_total", "n_fim_de_semana", "pct_fim_de_semana",
        "n_dezembro", "n_provavel_saque", "pct_provavel_saque",
    ]].to_markdown(index=False, disable_numparse=True)

    repetidos = valores_repetidos_mesmo_portador(df)
    if not repetidos.empty:
        repetidos_fmt = repetidos.head(20).copy()
        repetidos_fmt["valor"] = repetidos_fmt["valor"].map(fmt_brl)
        repetidos_md = repetidos_fmt.to_markdown(index=False, disable_numparse=True)
    else:
        repetidos_md = "_Nenhum portador com o mesmo valor repetido ≥3 vezes na amostra._"

    n_fds = int(df["eh_fim_de_semana"].sum())
    n_dez = int(df["eh_dezembro"].sum())
    n_saque = int(df["eh_provavel_saque"].sum())

    linhas = f"""# Cartão de Pagamento do Governo Federal (CPGF) — tarefa 3.6

Gerado por `analises/12_cartoes.py`. Amostra: mesmas 15 instituições das
tarefas 3.2/3.3, transações de {ANO_INICIO} a {ANO_FIM}, CPGF (tipoCartao=1).
{n_brutos} transações brutas coletadas.

## 1. Limitações desta coleta

- **Detecção de saque:** o payload de `/cartoes` não tem campo explícito
  distinguindo saque de compra — a coluna `eh_provavel_saque` é uma
  heurística por nome do estabelecimento (contém "BANCO", "CAIXA ECON",
  "SAQUE" ou "CAIXA ELETRO"), não uma classificação oficial da fonte.
- **Possível truncamento na coleta do EBSERH:** a API retornou um erro
  HTTP 400 ("Erro ao executar a consulta") na página 175 da consulta do
  EBSERH — um erro genérico do servidor, não do cliente. O código de
  coleta (`sucuri.api.requisitar`/`coletar_paginado`) trata qualquer
  página que não retorne dados como "fim da paginação", **indistinguível
  de um erro transitório do servidor** — os 2.610 registros do EBSERH
  reportados abaixo (exatamente 174 páginas completas × 15) podem não ser
  o total real se houver mais páginas depois da 175. Não corrigido nesta
  tarefa; uma melhoria futura seria distinguir erro de fim-de-dados e
  tentar novamente daquele ponto.

## 2. Resumo de red flags por instituição

{resumo_md}

**Leitura:** {n_fds} transações em fim de semana e {n_dez} em dezembro no
total da amostra — datas atípicas para despesa administrativa rotineira
(não em si prova de irregularidade: viagens a serviço, eventos, plantões
de unidades de saúde como o Hospital de Clínicas legitimamente geram
gasto fora do horário comercial). {n_saque} transações classificadas como
provável saque pela heurística acima.

## 3. Valores repetidos pelo mesmo portador (≥3 ocorrências)

{repetidos_md}

**Leitura:** o mesmo portador com o mesmo valor exato repetido várias
vezes pode ser uma despesa recorrente legítima (ex.: assinatura mensal,
combustível com preço estável) ou um padrão a checar manualmente —
regra aqui é puramente descritiva, sem limiar de valor associado (ao
contrário do fracionamento de contratos, o CPGF não tem um teto de
dispensa formalmente análogo disponível nesta fonte).

Os dois primeiros casos (21× e 20×, ambos no Hospital de Clínicas de Porto
Alegre) têm frequência muito próxima de mensal ao longo dos ~35 meses da
janela de coleta (2023–2025) — leitura mais provável: pagamento fixo
recorrente (ex.: plantão, ajuda de custo mensal), não fracionamento de
despesa pontual. Casos com poucas ocorrências (5–8×) espalhadas de forma
menos regular no tempo são candidatos mais interessantes para checagem
manual do que os de maior contagem.

## 4. Dados salvos

`dados/cpgf_mec.parquet` — uma linha por transação coletada.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    print("Coletando CPGF...")
    registros = coletar_tudo(sessao)

    caminho_raw = DIR_DADOS / "raw" / "cpgf_mec_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df = construir_df_cartoes(registros)
    if not df.empty:
        df.to_parquet(DIR_DADOS / "cpgf_mec.parquet", index=False)
        print(f"Salvo: dados/cpgf_mec.parquet ({len(df)} linhas)")

    conteudo = gerar_relatorio(df, len(registros))
    caminho_md = DIR_RELATORIOS / "12_cartoes.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
