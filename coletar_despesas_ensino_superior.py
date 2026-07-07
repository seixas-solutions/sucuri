#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coleta de despesas federais com Educação de Nível Superior (Ensino Superior)
a partir da API de Dados do Portal da Transparência (gov.br) e preparação dos
conjuntos de dados para análise de ciência de dados / detecção de anomalias.

Fonte: https://api.portaldatransparencia.gov.br/api-de-dados

São produzidos DOIS conjuntos complementares:

  (A) Painel funcional-programático  ->  dados/despesas_ensino_superior.*
      Endpoint /despesas/por-funcional-programatica
      Filtro: função 12 (Educação) + subfunção 364 (Ensino Superior).
      Precisão de subfunção, granularidade por programa/ação, nível federal.
      Este endpoint NÃO permite recorte por órgão.

  (B) Painel por instituição          ->  dados/despesas_por_instituicao.*
      Endpoint /despesas/por-orgao, iterando os órgãos do Ministério da
      Educação (órgão superior 26000): universidades federais, institutos
      federais/CEFETs, hospitais universitários (EBSERH), CAPES, FNDE/FIES etc.
      IMPORTANTE: aqui os valores são o TOTAL do órgão (todas as funções),
      pois este endpoint não filtra por subfunção. Para universidades e
      institutos federais a despesa é majoritariamente de ensino superior,
      mas o número não é estritamente a subfunção 364 (use o painel A para
      isso). O painel B viabiliza a comparação entre instituições e a
      detecção de anomalias por instituição e entre pares.

O programa:
  1. Lê a chave da API do arquivo .env (variável GOVBR_API_KEY).
  2. Percorre um intervalo de anos, paginando cada consulta até esgotar.
  3. Respeita o limite de requisições da API (espera + novas tentativas).
  4. Converte os valores monetários do formato brasileiro para float.
  5. Cria variáveis derivadas úteis para detecção de anomalias.
  6. Salva dados brutos (JSON) e conjuntos tratados (CSV + Parquet) + dicionário.

Uso:
    python coletar_despesas_ensino_superior.py                    # ambos, 2014..atual
    python coletar_despesas_ensino_superior.py --ano-inicio 2018 --ano-fim 2025
    python coletar_despesas_ensino_superior.py --somente funcional
    python coletar_despesas_ensino_superior.py --somente instituicao
    python coletar_despesas_ensino_superior.py --env /caminho/.env
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
API_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
ENDPOINT_FUNCIONAL = "/despesas/por-funcional-programatica"
ENDPOINT_POR_ORGAO = "/despesas/por-orgao"

CODIGO_FUNCAO_EDUCACAO = "12"              # Função orçamentária: Educação
CODIGO_SUBFUNCAO_ENSINO_SUPERIOR = "364"   # Subfunção: Ensino Superior
CODIGO_ORGAO_SUPERIOR_MEC = "26000"        # Ministério da Educação

# A API do Portal da Transparência limita a ~90 requisições/minuto no horário
# comercial (6h–24h). Uma pausa de 0,8s entre chamadas mantém folga segura.
PAUSA_ENTRE_REQUISICOES_S = 0.8
MAX_TENTATIVAS = 5
TIMEOUT_S = 60

ENV_PATH_PADRAO = "/Users/leseixas/.env"
NOME_CHAVE_ENV = "GOVBR_API_KEY"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("despesas_ensino_superior")


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def carregar_chave_api(env_path: str) -> str:
    """Carrega a chave da API a partir do arquivo .env (sem imprimi-la)."""
    valores = dotenv_values(env_path)
    chave = valores.get(NOME_CHAVE_ENV) or os.environ.get(NOME_CHAVE_ENV)
    if not chave:
        log.error("Chave '%s' não encontrada em %s nem no ambiente.", NOME_CHAVE_ENV, env_path)
        sys.exit(1)
    log.info("Chave da API carregada de %s (valor ocultado).", env_path)
    return chave.strip()


def brl_para_float(valor: str | float | None) -> float:
    """Converte '1.059.473.395,24' -> 1059473395.24. Vazio/None -> 0.0."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return math.nan


def _razao_segura(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Divisão elemento a elemento retornando NaN quando o denominador é 0."""
    den = denominador.where(denominador != 0)
    return numerador / den


def classificar_instituicao(descricao: str) -> str:
    """Classifica o órgão do MEC em categorias para comparação entre pares."""
    d = (descricao or "").upper()
    if "HOSPITAL" in d or "SERVIÇOS HOSPITALARES" in d or "SERVICOS HOSPITALARES" in d:
        return "Hospitalar (EBSERH)"
    if "UNIVERSIDADE" in d:
        return "Universidade Federal"
    if any(t in d for t in ("INSTITUTO FEDERAL", "CENTRO FEDERAL", "CEFET", "ESCOLA TÉCNICA", "ESCOLA TECNICA")):
        return "Instituto/CEFET/Escola Técnica"
    if "APERFEIÇOAMENTO" in d or "APERFEICOAMENTO" in d or "CAPES" in d:
        return "CAPES"
    if "FUNDO" in d or "FINANCIAMENTO AO ESTUDANTE" in d:
        return "Fundo (FNDE/FIES)"
    if "COLÉGIO" in d or "COLEGIO" in d:
        return "Educação Básica"
    return "Outros / Administração"


# --------------------------------------------------------------------------- #
# Coleta genérica (com paginação, limite de taxa e novas tentativas)
# --------------------------------------------------------------------------- #
def criar_sessao(chave_api: str) -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update(
        {
            "chave-api-dados": chave_api,
            "Accept": "application/json",
            "User-Agent": "coletor-despesas-ensino-superior/2.0",
        }
    )
    return sessao


def requisitar(sessao: requests.Session, endpoint: str, params: dict) -> list[dict]:
    """Requisição única com backoff exponencial para 429/5xx/erros de rede."""
    url = f"{API_BASE}{endpoint}"
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = sessao.get(url, params=params, timeout=TIMEOUT_S)
        except requests.RequestException as exc:
            espera = PAUSA_ENTRE_REQUISICOES_S * (2 ** tentativa)
            log.warning("Erro de rede (%s). Nova tentativa em %.1fs.", exc, espera)
            time.sleep(espera)
            continue

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            espera = PAUSA_ENTRE_REQUISICOES_S * (2 ** tentativa) + 2
            log.warning("HTTP 429 (limite). Aguardando %.1fs.", espera)
            time.sleep(espera)
            continue
        if resp.status_code in (500, 502, 503, 504):
            espera = PAUSA_ENTRE_REQUISICOES_S * (2 ** tentativa)
            log.warning("HTTP %s. Nova tentativa em %.1fs.", resp.status_code, espera)
            time.sleep(espera)
            continue
        log.error("HTTP %s inesperado (%s %s): %s", resp.status_code, endpoint, params, resp.text[:200])
        return []
    log.error("Falha após %s tentativas (%s %s).", MAX_TENTATIVAS, endpoint, params)
    return []


def coletar_paginado(sessao: requests.Session, endpoint: str, params_base: dict, rotulo: str) -> list[dict]:
    """Percorre todas as páginas de uma consulta até receber página vazia."""
    registros: list[dict] = []
    pagina = 1
    while True:
        params = dict(params_base, pagina=pagina)
        dados = requisitar(sessao, endpoint, params)
        if not dados:
            break
        registros.extend(dados)
        log.info("  %s | página %02d | +%d (acum. %d)", rotulo, pagina, len(dados), len(registros))
        pagina += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES_S)
    return registros


def coletar_intervalo(sessao, endpoint, params_por_ano, ano_inicio, ano_fim, nome) -> list[dict]:
    """Coleta um intervalo de anos aplicando `params_por_ano(ano)` a cada ano."""
    todos: list[dict] = []
    for ano in range(ano_inicio, ano_fim + 1):
        log.info("[%s] coletando ano %s ...", nome, ano)
        registros = coletar_paginado(sessao, endpoint, params_por_ano(ano), f"{nome} {ano}")
        if not registros:
            log.info("[%s] ano %s: sem dados.", nome, ano)
        todos.extend(registros)
    return todos


# --------------------------------------------------------------------------- #
# (A) Painel funcional-programático — função 12 / subfunção 364
# --------------------------------------------------------------------------- #
def construir_df_funcional(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if df.empty:
        return df

    for col in ("empenhado", "liquidado", "pago"):
        df[col] = df[col].map(brl_para_float)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["chave_serie"] = df["codigoPrograma"].astype(str) + "-" + df["codigoAcao"].astype(str)

    df = _indicadores_execucao(df)
    df = _features_serie_temporal(df, chave="chave_serie")
    df = _consolidar_flags(df)

    colunas = [
        "ano", "codigoFuncao", "funcao", "codigoSubfuncao", "subfuncao",
        "codigoPrograma", "programa", "codigoAcao", "acao", "chave_serie",
        "empenhado", "liquidado", "pago",
        "taxa_liquidacao", "taxa_pagamento", "valor_a_liquidar", "restos_a_pagar",
        "variacao_pago_aa", "zscore_pago", "zscore_robusto_pago",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado",
        "flag_valor_negativo", "flag_anomalia_zscore", "flag_anomalia_robusto",
        "flag_salto_anual", "flag_anomalia",
    ]
    return df[[c for c in colunas if c in df.columns]]


# --------------------------------------------------------------------------- #
# (B) Painel por instituição — órgãos do MEC
# --------------------------------------------------------------------------- #
def construir_df_instituicao(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if df.empty:
        return df

    for col in ("empenhado", "liquidado", "pago"):
        df[col] = df[col].map(brl_para_float)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["chave_serie"] = df["codigoOrgao"].astype(str)
    df["tipo_instituicao"] = df["orgao"].map(classificar_instituicao)

    df = _indicadores_execucao(df)
    # Série temporal por instituição (evolução ao longo dos anos).
    df = _features_serie_temporal(df, chave="chave_serie")

    # Comparação ENTRE PARES: z-score do valor pago entre instituições do mesmo
    # tipo, no mesmo ano. Sinaliza instituição atípica frente aos seus pares.
    g = df.groupby(["ano", "tipo_instituicao"])["pago"]
    df["zscore_pago_entre_pares"] = (df["pago"] - g.transform("mean")) / g.transform("std").replace(0, pd.NA)
    df["flag_atipico_entre_pares"] = df["zscore_pago_entre_pares"].abs() > 3

    df = _consolidar_flags(df, extra=["flag_atipico_entre_pares"])

    colunas = [
        "ano", "codigoOrgaoSuperior", "orgaoSuperior",
        "codigoOrgao", "orgao", "tipo_instituicao", "chave_serie",
        "empenhado", "liquidado", "pago",
        "taxa_liquidacao", "taxa_pagamento", "valor_a_liquidar", "restos_a_pagar",
        "variacao_pago_aa", "zscore_pago", "zscore_robusto_pago", "zscore_pago_entre_pares",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado",
        "flag_valor_negativo", "flag_anomalia_zscore", "flag_anomalia_robusto",
        "flag_salto_anual", "flag_atipico_entre_pares", "flag_anomalia",
    ]
    return df[[c for c in colunas if c in df.columns]]


# --------------------------------------------------------------------------- #
# Engenharia de variáveis compartilhada
# --------------------------------------------------------------------------- #
def _indicadores_execucao(df: pd.DataFrame) -> pd.DataFrame:
    df["taxa_liquidacao"] = _razao_segura(df["liquidado"], df["empenhado"])
    df["taxa_pagamento"] = _razao_segura(df["pago"], df["empenhado"])
    df["valor_a_liquidar"] = df["empenhado"] - df["liquidado"]
    df["restos_a_pagar"] = df["liquidado"] - df["pago"]
    df["flag_pago_maior_empenhado"] = df["pago"] > df["empenhado"] + 0.005
    df["flag_liquidado_maior_empenhado"] = df["liquidado"] > df["empenhado"] + 0.005
    df["flag_valor_negativo"] = (df["empenhado"] < 0) | (df["liquidado"] < 0) | (df["pago"] < 0)
    return df


def _features_serie_temporal(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Variação anual e z-scores (clássico e robusto) do valor pago por série."""
    df = df.sort_values([chave, "ano"]).reset_index(drop=True)
    grupo = df.groupby(chave)["pago"]

    df["variacao_pago_aa"] = grupo.pct_change()

    media, desvio = grupo.transform("mean"), grupo.transform("std")
    df["zscore_pago"] = (df["pago"] - media) / desvio.replace(0, pd.NA)

    mediana = grupo.transform("median")
    mad = grupo.transform(lambda s: (s - s.median()).abs().median())
    df["zscore_robusto_pago"] = 0.6745 * (df["pago"] - mediana) / mad.replace(0, pd.NA)

    df["flag_anomalia_zscore"] = df["zscore_pago"].abs() > 3
    df["flag_anomalia_robusto"] = df["zscore_robusto_pago"].abs() > 3.5
    df["flag_salto_anual"] = df["variacao_pago_aa"].abs() > 1.0
    return df


def _consolidar_flags(df: pd.DataFrame, extra: list[str] | None = None) -> pd.DataFrame:
    flags = [
        "flag_anomalia_zscore", "flag_anomalia_robusto", "flag_salto_anual",
        "flag_pago_maior_empenhado", "flag_liquidado_maior_empenhado", "flag_valor_negativo",
    ] + (extra or [])
    consolidado = pd.Series(False, index=df.index)
    for f in flags:
        consolidado |= df[f].fillna(False)
    df["flag_anomalia"] = consolidado
    return df


# --------------------------------------------------------------------------- #
# Persistência
# --------------------------------------------------------------------------- #
def salvar_dataset(df: pd.DataFrame, registros: list[dict], dir_saida: Path, nome_base: str) -> None:
    dir_raw = dir_saida / "raw"
    dir_saida.mkdir(parents=True, exist_ok=True)
    dir_raw.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d")

    caminho_raw = dir_raw / f"{nome_base}_raw_{carimbo}.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Salvo bruto: %s (%d registros)", caminho_raw, len(registros))

    if df.empty:
        log.warning("[%s] DataFrame vazio — nada tratado a salvar.", nome_base)
        return

    caminho_csv = dir_saida / f"{nome_base}.csv"
    df.to_csv(caminho_csv, index=False, encoding="utf-8")
    log.info("Salvo CSV: %s", caminho_csv)
    try:
        caminho_pq = dir_saida / f"{nome_base}.parquet"
        df.to_parquet(caminho_pq, index=False)
        log.info("Salvo Parquet: %s", caminho_pq)
    except Exception as exc:
        log.warning("Não foi possível salvar Parquet (%s). CSV disponível.", exc)


def escrever_dicionario(dir_saida: Path) -> None:
    (dir_saida / "DICIONARIO.md").write_text(DICIONARIO, encoding="utf-8")
    log.info("Salvo dicionário: %s", dir_saida / "DICIONARIO.md")


DICIONARIO = """# Dicionário de dados — Despesas com Ensino Superior

Fonte: Portal da Transparência (gov.br). Valores em reais (R$).

## Conjunto A — `despesas_ensino_superior.*` (funcional-programático)
Endpoint `/despesas/por-funcional-programatica`, função 12 (Educação),
subfunção 364 (Ensino Superior). Nível federal, por programa/ação.

| Coluna | Descrição |
|--------|-----------|
| ano | Ano do exercício orçamentário |
| codigoFuncao / funcao | Função (12 = Educação) |
| codigoSubfuncao / subfuncao | Subfunção (364 = Ensino Superior) |
| codigoPrograma / programa | Programa orçamentário |
| codigoAcao / acao | Ação orçamentária |
| chave_serie | Série temporal: programa-ação |
| empenhado / liquidado / pago | Estágios da despesa (R$) |

## Conjunto B — `despesas_por_instituicao.*` (por órgão do MEC)
Endpoint `/despesas/por-orgao`, órgão superior 26000 (Ministério da Educação).
Cada linha é o TOTAL do órgão no ano (todas as funções). Para universidades e
institutos federais a despesa é majoritariamente ensino superior, mas não é
estritamente a subfunção 364 — use o Conjunto A para precisão de subfunção.

| Coluna | Descrição |
|--------|-----------|
| ano | Ano do exercício |
| codigoOrgaoSuperior / orgaoSuperior | Sempre 26000 / Ministério da Educação |
| codigoOrgao / orgao | Instituição (universidade, IF, hospital, fundo...) |
| tipo_instituicao | Categoria derivada para comparação entre pares |
| chave_serie | Série temporal: código do órgão |
| empenhado / liquidado / pago | Estágios da despesa (R$) |

## Variáveis derivadas (ambos os conjuntos)
| Coluna | Descrição |
|--------|-----------|
| taxa_liquidacao | liquidado / empenhado |
| taxa_pagamento | pago / empenhado |
| valor_a_liquidar | empenhado - liquidado |
| restos_a_pagar | liquidado - pago |
| variacao_pago_aa | Variação % do pago vs. ano anterior (por série) |
| zscore_pago | z-score do pago no histórico da série |
| zscore_robusto_pago | z-score robusto (mediana/MAD) do pago |
| zscore_pago_entre_pares | (só B) z-score do pago entre instituições do mesmo tipo, no mesmo ano |
| flag_pago_maior_empenhado | Incoerência: pago > empenhado |
| flag_liquidado_maior_empenhado | Incoerência: liquidado > empenhado |
| flag_valor_negativo | Algum valor negativo |
| flag_anomalia_zscore | \\|zscore_pago\\| > 3 |
| flag_anomalia_robusto | \\|zscore_robusto_pago\\| > 3,5 |
| flag_salto_anual | \\|variacao_pago_aa\\| > 100% |
| flag_atipico_entre_pares | (só B) \\|zscore_pago_entre_pares\\| > 3 |
| flag_anomalia | Consolidação (OU lógico) de todas as flags acima |

## Sugestões para detecção de anomalias
- Modelos não supervisionados (Isolation Forest, LOF, DBSCAN) sobre
  `[empenhado, liquidado, pago, taxa_pagamento, variacao_pago_aa, zscore_pago]`.
- No Conjunto B, `zscore_pago_entre_pares` compara cada instituição aos pares
  do mesmo tipo — bom para achar instituições fora do padrão em um dado ano.
- As colunas `flag_*` servem como regras de negócio e rótulos fracos para
  validar os modelos não supervisionados.
"""


def resumir(df: pd.DataFrame, nome: str) -> None:
    if df.empty:
        return
    anos = f"{int(df['ano'].min())}–{int(df['ano'].max())}"
    total = f"{df['pago'].sum():,.2f}"
    n_anom = int(df["flag_anomalia"].sum())
    log.info("[%s] %d registros | anos %s | total pago R$ %s | %d possíveis anomalias",
             nome, len(df), anos, total, n_anom)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ano_atual = datetime.now().year
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ano-inicio", type=int, default=2014)
    parser.add_argument("--ano-fim", type=int, default=ano_atual)
    parser.add_argument("--env", default=ENV_PATH_PADRAO, help="Caminho do arquivo .env")
    parser.add_argument("--dir-saida", default="dados", help="Diretório de saída")
    parser.add_argument("--somente", choices=["funcional", "instituicao"], default=None,
                        help="Coletar apenas um dos painéis (padrão: ambos)")
    args = parser.parse_args()

    chave = carregar_chave_api(args.env)
    sessao = criar_sessao(chave)
    dir_saida = Path(args.dir_saida)

    # (A) Funcional-programático
    if args.somente in (None, "funcional"):
        log.info("=== (A) Painel funcional-programático: Ensino Superior (%s a %s) ===",
                 args.ano_inicio, args.ano_fim)
        registros = coletar_intervalo(
            sessao, ENDPOINT_FUNCIONAL,
            lambda ano: {"ano": ano, "funcao": CODIGO_FUNCAO_EDUCACAO,
                         "subfuncao": CODIGO_SUBFUNCAO_ENSINO_SUPERIOR},
            args.ano_inicio, args.ano_fim, "funcional",
        )
        df_a = construir_df_funcional(registros)
        salvar_dataset(df_a, registros, dir_saida, "despesas_ensino_superior")
        resumir(df_a, "funcional")

    # (B) Por instituição (órgãos do MEC)
    if args.somente in (None, "instituicao"):
        log.info("=== (B) Painel por instituição: órgãos do MEC (%s a %s) ===",
                 args.ano_inicio, args.ano_fim)
        registros = coletar_intervalo(
            sessao, ENDPOINT_POR_ORGAO,
            lambda ano: {"ano": ano, "orgaoSuperior": CODIGO_ORGAO_SUPERIOR_MEC},
            args.ano_inicio, args.ano_fim, "instituicao",
        )
        df_b = construir_df_instituicao(registros)
        salvar_dataset(df_b, registros, dir_saida, "despesas_por_instituicao")
        resumir(df_b, "instituicao")

    escrever_dicionario(dir_saida)
    log.info("Concluído.")


if __name__ == "__main__":
    main()
