"""Coleta de dados do IBGE via sidrapy (API SIDRA) e utilidades de
cruzamento com os dados do Portal da Transparência.

A API SIDRA é pública e não exige chave nem cadastro (nenhuma relação com
`GOVBR_API_KEY`). A coleta usa a biblioteca `sidrapy`
(https://pypi.org/project/sidrapy/), wrapper oficial-comunitário de
https://apisidra.ibge.gov.br/.

Tabelas usadas neste projeto:
- 6579 — População residente estimada (variável 9324), níveis 1 (Brasil) e
  3 (UF). A série tem lacunas nos anos de Censo/transição (ex.: 2022, 2023)
  — ver `interpolar_anos_faltantes` para o tratamento.
- 5938 — Contas Regionais: PIB a preços correntes (variável 37, mil R$),
  nível 3 (UF). Publicada com defasagem de ~2 anos (última: 2022).
"""

from __future__ import annotations

import logging

import pandas as pd
import sidrapy

TABELA_POPULACAO = "6579"
VARIAVEL_POPULACAO = "9324"
TABELA_PIB_UF = "5938"
VARIAVEL_PIB = "37"

NIVEL_BRASIL = "1"  # nível territorial da SIDRA (não confundir com N1/N3 da API de agregados)
NIVEL_UF = "3"

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


def coletar_tabela_sidra(
    tabela: str, variavel: str, periodo: str, nivel: str = NIVEL_UF
) -> pd.DataFrame:
    """Baixa uma tabela da SIDRA via sidrapy e a normaliza com
    `normalizar_sidra`. `periodo` no formato da SIDRA (ex.: "2014-2025")."""
    bruto = sidrapy.get_table(
        table_code=tabela,
        territorial_level=nivel,
        ibge_territorial_code="all",
        variable=variavel,
        period=periodo,
    )
    return normalizar_sidra(bruto)


def normalizar_sidra(bruto: pd.DataFrame) -> pd.DataFrame:
    """Achata o retorno do sidrapy em `(localidade_id, localidade, ano, valor)`.

    O sidrapy devolve as dimensões como pares de colunas D1C/D1N, D2C/D2N, ...
    cuja ordem varia conforme a tabela; a primeira linha do DataFrame contém
    os rótulos humanos de cada coluna (ex.: "Ano", "Unidade da Federação") e
    é usada aqui para identificar qual par é o ano e qual é o território —
    nunca posições fixas. Marcadores não numéricos da SIDRA ("-", "..",
    "...", "X") viram NaN.
    """
    if bruto.empty:
        return pd.DataFrame(columns=["localidade_id", "localidade", "ano", "valor"])

    rotulos = bruto.iloc[0]
    dados = bruto.iloc[1:]

    col_ano = None
    col_territorio = None
    for codigo in bruto.columns:
        if not (codigo.startswith("D") and codigo.endswith("N")):
            continue
        rotulo = str(rotulos[codigo])
        if rotulo == "Ano":
            col_ano = codigo
        elif rotulo not in ("Variável", "Ano"):
            col_territorio = codigo
    if col_ano is None or col_territorio is None:
        raise ValueError(
            "Retorno da SIDRA sem dimensão 'Ano' e/ou território reconhecível "
            f"(rótulos: {[str(rotulos[c]) for c in bruto.columns]})."
        )

    return pd.DataFrame(
        {
            "localidade_id": dados[col_territorio.replace("N", "C")].values,
            "localidade": dados[col_territorio].values,
            "ano": dados[col_ano].astype(int).values,
            "valor": pd.to_numeric(dados["V"], errors="coerce").values,
        }
    )


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
