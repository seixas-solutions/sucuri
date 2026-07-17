"""Cliente da API de Dados do Portal da Transparência (gov.br)."""

from __future__ import annotations

import logging
import os
import sys
import time

import requests
from dotenv import dotenv_values

API_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
ENDPOINT_FUNCIONAL = "/despesas/por-funcional-programatica"
ENDPOINT_POR_ORGAO = "/despesas/por-orgao"

# Endpoints da Fase 3 (enriquecimento — ver src/sucuri/coletores/).
ENDPOINT_DESPESAS_DOCUMENTOS = "/despesas/documentos"
ENDPOINT_CONTRATOS = "/contratos"
ENDPOINT_LICITACOES = "/licitacoes"
ENDPOINT_CEIS = "/ceis"
ENDPOINT_CNEP = "/cnep"
ENDPOINT_ACORDOS_LENIENCIA = "/acordos-leniencia"
ENDPOINT_CONVENIOS = "/convenios"
ENDPOINT_CARTOES = "/cartoes"
ENDPOINT_EMENDAS = "/emendas"

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

log = logging.getLogger("sucuri.api")


def carregar_chave_api(env_path: str) -> str:
    """Carrega a chave da API a partir do arquivo .env (sem imprimi-la)."""
    valores = dotenv_values(env_path)
    chave = valores.get(NOME_CHAVE_ENV) or os.environ.get(NOME_CHAVE_ENV)
    if not chave:
        log.error("Chave '%s' não encontrada em %s nem no ambiente.", NOME_CHAVE_ENV, env_path)
        sys.exit(1)
    log.info("Chave da API carregada de %s (valor ocultado).", env_path)
    return chave.strip()


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
