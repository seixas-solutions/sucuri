"""Coletor do Cartão de Pagamento do Governo Federal (CPGF) — tarefa 3.6.

Endpoint `/cartoes`: filtra por `codigoOrgao` + `mesExtratoInicio`/
`mesExtratoFim` (mês/ano) + `tipoCartao` (1=CPGF, 2=CPCC, 3=CPDC — aqui
sempre CPGF, o cartão de uso mais comum e o citado no ROADMAP).

**Limitação conhecida:** o payload não tem um campo explícito
distinguindo saque de compra — a heurística usada aqui (nome do
estabelecimento contendo termos bancários) é aproximada, não uma
classificação oficial da fonte.
"""

from __future__ import annotations

import pandas as pd

from sucuri.api import ENDPOINT_CARTOES, coletar_paginado
from sucuri.utils import brl_para_float

TERMOS_SAQUE = ("BANCO", "CAIXA ECON", "SAQUE", "CAIXA ELETRO")


def coletar_cartoes(sessao, codigo_orgao: str, ano_inicio: int, ano_fim: int, tipo_cartao: int = 1) -> list[dict]:
    params = {
        "codigoOrgao": codigo_orgao,
        "mesExtratoInicio": f"01/{ano_inicio}",
        "mesExtratoFim": f"12/{ano_fim}",
        "tipoCartao": tipo_cartao,
    }
    return coletar_paginado(sessao, ENDPOINT_CARTOES, params, f"cartoes orgao={codigo_orgao}")


def construir_df_cartoes(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        ug = r.get("unidadeGestora") or {}
        orgao_vinculado = ug.get("orgaoVinculado") or {}
        estabelecimento = r.get("estabelecimento") or {}
        portador = r.get("portador") or {}
        nome_estab = (estabelecimento.get("nome") or "").upper()
        linhas.append({
            "id": r.get("id"),
            "codigoOrgao": orgao_vinculado.get("codigoSIAFI"),
            "orgao": orgao_vinculado.get("nome"),
            "dataTransacao": r.get("dataTransacao"),
            "valor": brl_para_float(r.get("valorTransacao")),
            "estabelecimentoNome": estabelecimento.get("nome"),
            "estabelecimentoCnpjCpf": estabelecimento.get("cnpjFormatado") or estabelecimento.get("cpfFormatado"),
            "portadorCpf": portador.get("cpfFormatado"),
            "portadorNome": portador.get("nome"),
            "eh_provavel_saque": any(t in nome_estab for t in TERMOS_SAQUE),
        })
    df = pd.DataFrame(linhas)
    df["dataTransacao"] = pd.to_datetime(df["dataTransacao"], format="%d/%m/%Y", errors="coerce")
    df["diaSemana"] = df["dataTransacao"].dt.dayofweek  # 5=sábado, 6=domingo
    df["eh_fim_de_semana"] = df["diaSemana"].isin([5, 6])
    df["mes"] = df["dataTransacao"].dt.month
    df["ano"] = df["dataTransacao"].dt.year
    df["eh_dezembro"] = df["mes"] == 12
    return df


def resumo_red_flags_por_orgao(df: pd.DataFrame) -> pd.DataFrame:
    """Contagem de transações por órgão para cada regra de red flag."""
    if df.empty:
        return pd.DataFrame()
    resumo = df.groupby(["codigoOrgao", "orgao"]).agg(
        n_transacoes=("id", "count"),
        valor_total=("valor", "sum"),
        n_fim_de_semana=("eh_fim_de_semana", "sum"),
        n_dezembro=("eh_dezembro", "sum"),
        n_provavel_saque=("eh_provavel_saque", "sum"),
    ).reset_index()
    resumo["pct_fim_de_semana"] = resumo["n_fim_de_semana"] / resumo["n_transacoes"]
    resumo["pct_provavel_saque"] = resumo["n_provavel_saque"] / resumo["n_transacoes"]
    return resumo.sort_values("valor_total", ascending=False)


def valores_repetidos_mesmo_portador(df: pd.DataFrame, min_ocorrencias: int = 3) -> pd.DataFrame:
    """Portadores com o mesmo valor de transação repetido `min_ocorrencias`
    vezes ou mais (mesmo estabelecimento ou não) — padrão compatível com
    fracionamento de despesa em compras rotineiras via cartão."""
    if df.empty:
        return pd.DataFrame(columns=["portadorNome", "orgao", "valor", "n_ocorrencias"])
    contagem = (
        df.groupby(["portadorCpf", "portadorNome", "orgao", "valor"])
        .size()
        .reset_index(name="n_ocorrencias")
    )
    return contagem[contagem["n_ocorrencias"] >= min_ocorrencias].sort_values(
        "n_ocorrencias", ascending=False
    )
