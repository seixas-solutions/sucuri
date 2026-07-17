"""Coletor de contratos — tarefa 3.2 do ROADMAP.

Endpoint `/contratos`: filtra por `codigoOrgao` (o mesmo código de 5
dígitos do Conjunto B, sem a complicação de Unidade Gestora encontrada na
tarefa 3.1) + intervalo de datas — muito mais barato que
`/despesas/documentos` (paginado normalmente, não 1 requisição por dia).

Cada contrato já vem com `valorInicialCompra`/`valorFinalCompra` (a
diferença já reflete termos aditivos aplicados — não é preciso um segundo
endpoint para isso) e `modalidadeCompra` (texto livre; dispensa/
inexigibilidade aparecem como substring).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from sucuri.api import ENDPOINT_CONTRATOS, coletar_paginado
from sucuri.utils import razao_segura

TERMOS_DISPENSA_INEXIGIBILIDADE = ("DISPENSA", "INEXIGIBILIDADE")

# Limiar de dispensa de licitação por valor para compras/serviços em geral
# (Lei 14.133/2021, art. 75, inciso II — valor-base da lei; sujeito a
# atualização periódica por decreto de indexação, não considerada aqui).
# Usado só como referência de ordem de grandeza para o indício de
# fracionamento — não é o valor vigente exato em cada data de cada contrato.
LIMIAR_DISPENSA_REFERENCIA = 50_000.0


def coletar_contratos_orgao(
    sessao, codigo_orgao: str, data_inicial: date, data_final: date
) -> list[dict]:
    """Coleta todos os contratos de um órgão vigentes no intervalo pedido."""
    params = {
        "codigoOrgao": codigo_orgao,
        "dataInicial": data_inicial.strftime("%d/%m/%Y"),
        "dataFinal": data_final.strftime("%d/%m/%Y"),
    }
    return coletar_paginado(sessao, ENDPOINT_CONTRATOS, params, f"contratos orgao={codigo_orgao}")


def construir_df_contratos(registros: list[dict]) -> pd.DataFrame:
    """Achata os campos aninhados relevantes e calcula as features do
    ROADMAP: valor contratado/aditivado, prazo (dias),
    dispensa/inexigibilidade (bool)."""
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        ug = r.get("unidadeGestora") or {}
        orgao_vinculado = ug.get("orgaoVinculado") or {}
        fornecedor = r.get("fornecedor") or {}
        compra = r.get("compra") or {}
        modalidade = r.get("modalidadeCompra") or ""
        # O campo `numeroProcesso` no nível raiz do payload vem sempre
        # vazio ("Sem informação") — o valor real está aninhado em
        # `compra.numeroProcesso` (confirmado empiricamente; não documentado
        # no Swagger). Cai para o campo raiz só se o aninhado também faltar.
        linhas.append({
            "id": r.get("id"),
            "numero": r.get("numero"),
            "numeroProcesso": compra.get("numeroProcesso") or r.get("numeroProcesso"),
            "objeto": r.get("objeto"),
            "codigoOrgao": orgao_vinculado.get("codigoSIAFI"),
            "orgao": orgao_vinculado.get("nome"),
            "modalidadeCompra": modalidade,
            "eh_dispensa_ou_inexigibilidade": any(t in modalidade.upper() for t in TERMOS_DISPENSA_INEXIGIBILIDADE),
            "dataAssinatura": r.get("dataAssinatura"),
            "dataInicioVigencia": r.get("dataInicioVigencia"),
            "dataFimVigencia": r.get("dataFimVigencia"),
            "fornecedorCnpjCpf": fornecedor.get("cnpjFormatado") or fornecedor.get("cpfFormatado"),
            "fornecedorNome": fornecedor.get("nome"),
            "fornecedorTipo": fornecedor.get("tipo"),
            "valorInicialCompra": r.get("valorInicialCompra") or 0.0,
            "valorFinalCompra": r.get("valorFinalCompra") or 0.0,
        })
    df = pd.DataFrame(linhas)

    df["dataInicioVigencia"] = pd.to_datetime(df["dataInicioVigencia"], errors="coerce")
    df["dataFimVigencia"] = pd.to_datetime(df["dataFimVigencia"], errors="coerce")
    df["dataAssinatura"] = pd.to_datetime(df["dataAssinatura"], errors="coerce")
    df["ano"] = df["dataAssinatura"].dt.year
    df["prazo_dias"] = (df["dataFimVigencia"] - df["dataInicioVigencia"]).dt.days
    df["valor_aditivado"] = df["valorFinalCompra"] - df["valorInicialCompra"]
    df["pct_aditivado"] = razao_segura(df["valor_aditivado"], df["valorInicialCompra"])
    return df


def indice_herfindahl(df: pd.DataFrame, coluna_grupo: str = "codigoOrgao",
                       coluna_fornecedor: str = "fornecedorCnpjCpf",
                       coluna_valor: str = "valorFinalCompra") -> pd.DataFrame:
    """Índice Herfindahl-Hirschman (HHI) de concentração de fornecedores por
    grupo (padrão: por órgão), em escala 0–10.000 (soma dos market-shares
    percentuais ao quadrado). HHI > 2.500 é convencionalmente considerado
    "altamente concentrado" em análises antitruste; usado aqui só como
    referência de escala, não como limiar de acusação.
    """
    def _hhi(grupo: pd.DataFrame) -> float:
        total = grupo[coluna_valor].sum()
        if total <= 0:
            return float("nan")
        participacoes = grupo.groupby(coluna_fornecedor)[coluna_valor].sum() / total * 100
        return float((participacoes ** 2).sum())

    resultado = (
        df.groupby(coluna_grupo)
        .apply(_hhi, include_groups=False)
        .reset_index(name="hhi_fornecedores")
    )
    n_fornecedores = df.groupby(coluna_grupo)[coluna_fornecedor].nunique().reset_index(name="n_fornecedores")
    return resultado.merge(n_fornecedores, on=coluna_grupo)


def detectar_fracionamento(
    df: pd.DataFrame, min_ocorrencias: int = 2, limiar_valor: float = LIMIAR_DISPENSA_REFERENCIA
) -> pd.DataFrame:
    """Indício de fracionamento de despesa: múltiplos contratos por
    dispensa/inexigibilidade do mesmo (órgão, fornecedor, ano), cada um
    abaixo de `limiar_valor`, cuja SOMA ultrapassa o limiar — padrão
    compatível com fracionar uma compra maior em vários contratos pequenos
    para evitar a exigência de licitação. Regra explícita, não prova de
    fracionamento real (pode haver justificativa legítima para contratos
    repetidos e pequenos com o mesmo fornecedor).
    """
    candidatos = df[df["eh_dispensa_ou_inexigibilidade"] & (df["valorFinalCompra"] < limiar_valor)]
    if candidatos.empty:
        return pd.DataFrame(columns=[
            "codigoOrgao", "orgao", "fornecedorCnpjCpf", "fornecedorNome", "ano",
            "n_contratos", "valor_somado",
        ])
    agrupado = (
        candidatos.groupby(["codigoOrgao", "orgao", "fornecedorCnpjCpf", "fornecedorNome", "ano"])
        .agg(n_contratos=("id", "count"), valor_somado=("valorFinalCompra", "sum"))
        .reset_index()
    )
    indicio = agrupado[
        (agrupado["n_contratos"] >= min_ocorrencias) & (agrupado["valor_somado"] >= limiar_valor)
    ]
    return indicio.sort_values(["n_contratos", "valor_somado"], ascending=False)
