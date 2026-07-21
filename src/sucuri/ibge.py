"""Cliente da API de agregados do IBGE (SIDRA/servicodados) e utilidades de
cruzamento com os dados do Portal da Transparência.

A API é pública e não exige chave nem cadastro (diferente da API do Portal —
nenhuma relação com `GOVBR_API_KEY`). Documentação:
https://servicodados.ibge.gov.br/api/docs/agregados

Agregados usados neste projeto:
- 6579 — População residente estimada (variável 9324), níveis N1 (Brasil) e
  N3 (UF). A série tem lacunas nos anos de Censo/Contagem (ex.: 2007, 2010,
  2022) e em 2023 — ver `interpolar_anos_faltantes` para o tratamento.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
import requests

URL_AGREGADOS = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/"
    "{agregado}/periodos/{periodos}/variaveis/{variavel}"
)

AGREGADO_POPULACAO = "6579"
VARIAVEL_POPULACAO = "9324"

NIVEL_BRASIL = "N1"
NIVEL_UF = "N3"

PAUSA_ENTRE_REQUISICOES_S = 0.3  # API pública sem limite documentado; cortesia
TIMEOUT_S = 60

# Nome oficial (maiúsculas, com acentos — como aparece tanto no IBGE quanto no
# campo `localidadeDoGasto` das emendas) -> sigla da UF.
SIGLA_POR_NOME_UF = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPÁ": "AP", "AMAZONAS": "AM",
    "BAHIA": "BA", "CEARÁ": "CE", "DISTRITO FEDERAL": "DF",
    "ESPÍRITO SANTO": "ES", "GOIÁS": "GO", "MARANHÃO": "MA",
    "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG",
    "PARÁ": "PA", "PARAÍBA": "PB", "PARANÁ": "PR", "PERNAMBUCO": "PE",
    "PIAUÍ": "PI", "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS", "RONDÔNIA": "RO", "RORAIMA": "RR",
    "SANTA CATARINA": "SC", "SÃO PAULO": "SP", "SERGIPE": "SE",
    "TOCANTINS": "TO",
}

log = logging.getLogger("sucuri.ibge")


def consultar_agregado(
    agregado: str,
    variavel: str,
    periodos: list[int] | list[str],
    nivel: str = NIVEL_UF,
    sessao: requests.Session | None = None,
) -> list[dict]:
    """Consulta um agregado do IBGE para uma lista de períodos (anos).

    Retorna o payload JSON bruto da API (lista com uma entrada por variável).
    Períodos inexistentes no agregado são simplesmente omitidos da resposta,
    não geram erro.
    """
    sessao = sessao or requests.Session()
    url = URL_AGREGADOS.format(
        agregado=agregado,
        periodos="|".join(str(p) for p in periodos),
        variavel=variavel,
    )
    resp = sessao.get(url, params={"localidades": f"{nivel}[all]"}, timeout=TIMEOUT_S)
    resp.raise_for_status()
    time.sleep(PAUSA_ENTRE_REQUISICOES_S)
    return resp.json()


def extrair_series(payload: list[dict]) -> pd.DataFrame:
    """Achata o payload da API de agregados em colunas
    `(localidade_id, localidade, ano, valor)`.

    Valores não numéricos usados pelo IBGE como marcadores ("-", "...", "X",
    valor ausente) viram NaN.
    """
    linhas = []
    for variavel in payload:
        for resultado in variavel.get("resultados", []):
            for serie in resultado.get("series", []):
                localidade = serie.get("localidade", {})
                for ano, valor in serie.get("serie", {}).items():
                    linhas.append(
                        {
                            "localidade_id": localidade.get("id"),
                            "localidade": localidade.get("nome"),
                            "ano": int(ano),
                            "valor": pd.to_numeric(valor, errors="coerce"),
                        }
                    )
    return pd.DataFrame(linhas, columns=["localidade_id", "localidade", "ano", "valor"])


def interpolar_anos_faltantes(df: pd.DataFrame, anos: list[int]) -> pd.DataFrame:
    """Preenche, por localidade, os anos pedidos ausentes da série com
    interpolação linear entre os anos vizinhos disponíveis (sem extrapolar:
    anos fora do intervalo observado ficam NaN).

    Uso previsto: lacunas da série de estimativas populacionais (anos de
    Censo, ex.: 2022). Toda linha criada é marcada com `interpolado=True`
    para que as análises possam reportar a ressalva explicitamente.
    """
    completos = []
    for (loc_id, loc_nome), grupo in df.groupby(["localidade_id", "localidade"]):
        serie = grupo.set_index("ano")["valor"].sort_index()
        todos_anos = sorted(set(serie.index) | set(anos))
        reindexada = serie.reindex(todos_anos)
        preenchida = reindexada.interpolate(method="index", limit_area="inside")
        bloco = pd.DataFrame(
            {
                "localidade_id": loc_id,
                "localidade": loc_nome,
                "ano": preenchida.index,
                "valor": preenchida.values,
                "interpolado": reindexada.isna() & preenchida.notna(),
            }
        )
        completos.append(bloco[bloco["ano"].isin(anos)])
    if not completos:
        return df.assign(interpolado=False)
    return pd.concat(completos, ignore_index=True)


def extrair_uf(localidade_do_gasto: str | None) -> str | None:
    """Extrai a sigla da UF do campo `localidadeDoGasto` das emendas.

    Formatos observados na base (tarefa 3.7): "MUNICÍPIO - UF",
    "NOME DO ESTADO (UF)" e agregados sem UF definida ("Nacional", regiões,
    "MÚLTIPLO") — estes retornam None e devem ser reportados como não
    atribuíveis, nunca descartados silenciosamente.
    """
    if not localidade_do_gasto or not isinstance(localidade_do_gasto, str):
        return None
    texto = localidade_do_gasto.strip()
    if texto.upper().endswith("(UF)"):
        nome = texto[: texto.upper().rfind("(UF)")].strip().upper()
        return SIGLA_POR_NOME_UF.get(nome)
    if len(texto) > 5 and texto[-5:-2] == " - " and texto[-2:].isalpha() and texto[-2:].isupper():
        sigla = texto[-2:]
        return sigla if sigla in SIGLA_POR_NOME_UF.values() else None
    return None
