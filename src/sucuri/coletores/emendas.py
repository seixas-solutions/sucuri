"""Coletor de emendas parlamentares — tarefa 3.7 do ROADMAP.

**Limitação empírica descoberta nesta tarefa:** nem `/emendas` nem
`/emendas/documentos/{codigo}` expõem a instituição beneficiária
diretamente — `/emendas` só tem `localidadeDoGasto` (nível de UF, não de
órgão) e `/emendas/documentos/{codigo}` só tem o código do documento
(prefixado por um código de Unidade Gestora, mesmo problema de
código-UG-sem-mapeamento-público já encontrado na tarefa 3.1). Por isso o
recorte possível aqui é por **função/subfunção orçamentária**
(12/364 = Ensino Superior), não por instituição específica do Conjunto B
— ver `analises/13_emendas.py` para a análise no nível agregado.
"""

from __future__ import annotations

import pandas as pd

from sucuri.api import ENDPOINT_EMENDAS, coletar_paginado
from sucuri.utils import brl_para_float

CODIGO_FUNCAO_EDUCACAO = "12"
CODIGO_SUBFUNCAO_ENSINO_SUPERIOR = "364"


def coletar_emendas_ano(sessao, ano: int, codigo_funcao: str = CODIGO_FUNCAO_EDUCACAO,
                         codigo_subfuncao: str = CODIGO_SUBFUNCAO_ENSINO_SUPERIOR) -> list[dict]:
    params = {"ano": ano, "codigoFuncao": codigo_funcao, "codigoSubfuncao": codigo_subfuncao}
    return coletar_paginado(sessao, ENDPOINT_EMENDAS, params, f"emendas ano={ano}")


def coletar_emendas_intervalo(sessao, ano_inicio: int, ano_fim: int, **kwargs) -> list[dict]:
    registros: list[dict] = []
    for ano in range(ano_inicio, ano_fim + 1):
        registros.extend(coletar_emendas_ano(sessao, ano, **kwargs))
    return registros


def construir_df_emendas(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    linhas = []
    for r in registros:
        linhas.append({
            "codigoEmenda": r.get("codigoEmenda"),
            "ano": r.get("ano"),
            "tipoEmenda": r.get("tipoEmenda"),
            "autor": r.get("autor") or r.get("nomeAutor"),
            "localidadeDoGasto": r.get("localidadeDoGasto"),
            "funcao": r.get("funcao"),
            "subfuncao": r.get("subfuncao"),
            "valorEmpenhado": brl_para_float(r.get("valorEmpenhado")),
            "valorLiquidado": brl_para_float(r.get("valorLiquidado")),
            "valorPago": brl_para_float(r.get("valorPago")),
        })
    return pd.DataFrame(linhas)


ANOS_ELEITORAIS_MUNICIPAIS = {2016, 2020, 2024}
ANOS_ELEITORAIS_GERAIS = {2014, 2018, 2022}


def marcar_ano_eleitoral(df: pd.DataFrame, coluna_ano: str = "ano") -> pd.DataFrame:
    df = df.copy()
    todos_eleitorais = ANOS_ELEITORAIS_MUNICIPAIS | ANOS_ELEITORAIS_GERAIS
    df["ano_eleitoral"] = df[coluna_ano].isin(todos_eleitorais)
    return df
