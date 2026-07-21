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

A lógica reutilizável (conversão de valores, requisições, engenharia de
variáveis, persistência) vive no pacote `sucuri` (`src/sucuri/`). Este
arquivo é apenas a interface de linha de comando.

Uso:
    python coletar_despesas.py                    # ambos, 2014..atual
    python coletar_despesas.py --ano-inicio 2018 --ano-fim 2025
    python coletar_despesas.py --somente funcional
    python coletar_despesas.py --somente instituicao
    python coletar_despesas.py --incremental      # só anos novos/em aberto
    python coletar_despesas.py --env /caminho/.env
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from sucuri.api import (
    CODIGO_FUNCAO_EDUCACAO,
    CODIGO_ORGAO_SUPERIOR_MEC,
    CODIGO_SUBFUNCAO_ENSINO_SUPERIOR,
    ENDPOINT_FUNCIONAL,
    ENDPOINT_POR_ORGAO,
    ENV_PATH_PADRAO,
    carregar_chave_api,
    coletar_anos,
    criar_sessao,
)
from sucuri.features import construir_df_funcional, construir_df_instituicao
from sucuri.incremental import (
    ano_do_carimbo,
    anos_a_coletar,
    anos_presentes,
    carregar_registros,
    mesclar_registros,
    raw_mais_recente,
)
from sucuri.persistencia import escrever_dicionario, resumir, salvar_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("despesas_ensino_superior")


def coletar_painel(sessao, endpoint, params_por_ano, args, nome: str, nome_base: str) -> list[dict]:
    """Coleta um painel no intervalo pedido, integral ou incrementalmente.

    No modo incremental, reaproveita o bruto mais recente de `dados/raw/` e só
    requisita à API os anos ausentes ou ainda em aberto na última coleta
    (ver `sucuri.incremental`). Sem bruto anterior, cai na coleta integral.
    """
    dir_raw = Path(args.dir_saida) / "raw"
    caminho_anterior = raw_mais_recente(dir_raw, nome_base) if args.incremental else None
    if caminho_anterior is None:
        if args.incremental:
            log.info("[%s] sem bruto anterior em %s — coleta integral.", nome, dir_raw)
        return coletar_anos(sessao, endpoint, params_por_ano,
                            range(args.ano_inicio, args.ano_fim + 1), nome)

    antigos = carregar_registros(caminho_anterior)
    anos = anos_a_coletar(anos_presentes(antigos), args.ano_inicio, args.ano_fim,
                          ano_do_carimbo(caminho_anterior))
    log.info("[%s] incremental sobre %s: recoletando anos %s.",
             nome, caminho_anterior.name, anos or "nenhum")
    novos = coletar_anos(sessao, endpoint, params_por_ano, anos, nome)
    return mesclar_registros(antigos, novos, anos)


def main() -> None:
    ano_atual = datetime.now().year
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ano-inicio", type=int, default=2014)
    parser.add_argument("--ano-fim", type=int, default=ano_atual)
    parser.add_argument("--env", default=ENV_PATH_PADRAO, help="Caminho do arquivo .env")
    parser.add_argument("--dir-saida", default="dados", help="Diretório de saída")
    parser.add_argument("--somente", choices=["funcional", "instituicao"], default=None,
                        help="Coletar apenas um dos painéis (padrão: ambos)")
    parser.add_argument("--incremental", action="store_true",
                        help="Reaproveitar o bruto mais recente e coletar só anos "
                             "ausentes ou em aberto na última coleta")
    args = parser.parse_args()

    chave = carregar_chave_api(args.env)
    sessao = criar_sessao(chave)
    dir_saida = Path(args.dir_saida)

    # (A) Funcional-programático
    if args.somente in (None, "funcional"):
        log.info("=== (A) Painel funcional-programático: Ensino Superior (%s a %s) ===",
                 args.ano_inicio, args.ano_fim)
        registros = coletar_painel(
            sessao, ENDPOINT_FUNCIONAL,
            lambda ano: {"ano": ano, "funcao": CODIGO_FUNCAO_EDUCACAO,
                         "subfuncao": CODIGO_SUBFUNCAO_ENSINO_SUPERIOR},
            args, "funcional", "despesas_ensino_superior",
        )
        df_a = construir_df_funcional(registros)
        salvar_dataset(df_a, registros, dir_saida, "despesas_ensino_superior")
        resumir(df_a, "funcional")

    # (B) Por instituição (órgãos do MEC)
    if args.somente in (None, "instituicao"):
        log.info("=== (B) Painel por instituição: órgãos do MEC (%s a %s) ===",
                 args.ano_inicio, args.ano_fim)
        registros = coletar_painel(
            sessao, ENDPOINT_POR_ORGAO,
            lambda ano: {"ano": ano, "orgaoSuperior": CODIGO_ORGAO_SUPERIOR_MEC},
            args, "instituicao", "despesas_por_instituicao",
        )
        df_b = construir_df_instituicao(registros)
        salvar_dataset(df_b, registros, dir_saida, "despesas_por_instituicao")
        resumir(df_b, "instituicao")

    escrever_dicionario(dir_saida)
    log.info("Concluído.")


if __name__ == "__main__":
    main()
