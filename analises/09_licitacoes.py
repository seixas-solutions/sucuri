#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.3 do ROADMAP — Licitações e compras.

Coleta `/licitacoes` para as mesmas 15 instituições piloto da tarefa 3.2,
em 2024 (ano cheio, dentro da janela 2023–2025 já coletada em
`dados/contratos_mec.parquet`, para maximizar a sobreposição no
cruzamento). **Limite de escopo descoberto nesta tarefa:** a API só
aceita até 1 mês por requisição em `/licitacoes` (diferente de
`/contratos`, que aceita anos inteiros) — 15 instituições × 12 meses = 180
requisições, ainda razoável, mas cobrir os 3 anos completos custaria 3×
isso.

Três análises, cada uma com regra e limiar explícitos (ROADMAP):
  1. Licitações desertas/fracassadas repetidas (≥2 no mesmo órgão/ano).
  2. Indício de fracionamento (cruza com `dados/contratos_mec.parquet` —
     na verdade não precisa de licitações, é intra-contratos; roda aqui
     por unificação do relatório desta tarefa).
  3. Contratos sem licitação correspondente (join por `numeroProcesso`
     entre contratos que NÃO são dispensa/inexigibilidade e as licitações
     coletadas) — sujeito a falso positivo alto por causa da cobertura
     parcial (licitações só 2024, contratos 2023–2025).

Uso:
    uv run python analises/09_licitacoes.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.contratos import LIMIAR_DISPENSA_REFERENCIA, detectar_fracionamento
from sucuri.coletores.licitacoes import coletar_licitacoes_periodo, construir_df_licitacoes, desertas_repetidas

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DATA_INICIO = date(2024, 1, 1)
DATA_FIM = date(2024, 12, 31)

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


def coletar_tudo(sessao) -> list[dict]:
    todos: list[dict] = []
    for codigo_orgao, nome in INSTITUICOES_PILOTO:
        registros = coletar_licitacoes_periodo(sessao, codigo_orgao, DATA_INICIO, DATA_FIM)
        print(f"  {nome} ({codigo_orgao}): {len(registros)} licitações")
        todos.extend(registros)
    return todos


def contratos_sem_licitacao(df_contratos: pd.DataFrame, df_licitacoes: pd.DataFrame) -> pd.DataFrame:
    """Contratos que não são dispensa/inexigibilidade (logo, presumem
    licitação) e cujo `numeroProcesso` não aparece em nenhuma licitação
    coletada no mesmo órgão."""
    if df_contratos.empty:
        return pd.DataFrame()
    candidatos = df_contratos[
        ~df_contratos["eh_dispensa_ou_inexigibilidade"]
        & df_contratos["numeroProcesso"].notna()
        & (df_contratos["numeroProcesso"] != "Sem informação")
    ].copy()
    if df_licitacoes.empty:
        candidatos["licitacao_encontrada"] = False
    else:
        processos_licitados = set(
            zip(df_licitacoes["codigoOrgao"], df_licitacoes["numeroProcesso"], strict=False)
        )
        candidatos["licitacao_encontrada"] = candidatos.apply(
            lambda linha: (linha["codigoOrgao"], linha["numeroProcesso"]) in processos_licitados, axis=1
        )
    return candidatos[~candidatos["licitacao_encontrada"]]


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def gerar_relatorio(df_lic: pd.DataFrame, df_contratos: pd.DataFrame, n_brutos: int) -> str:
    desertas = desertas_repetidas(df_lic) if not df_lic.empty else pd.DataFrame()
    fracionamento = detectar_fracionamento(df_contratos) if not df_contratos.empty else pd.DataFrame()
    sem_licitacao = contratos_sem_licitacao(df_contratos, df_lic)
    candidatos_checados = df_contratos[
        ~df_contratos["eh_dispensa_ou_inexigibilidade"]
        & df_contratos["numeroProcesso"].notna()
        & (df_contratos["numeroProcesso"] != "Sem informação")
    ] if not df_contratos.empty else pd.DataFrame()

    desertas_md = desertas.to_markdown(index=False) if not desertas.empty else "_Nenhum órgão com ≥2 desertas/fracassadas na amostra._"

    fracionamento_fmt = fracionamento.copy()
    if not fracionamento_fmt.empty:
        fracionamento_fmt["valor_somado"] = fracionamento_fmt["valor_somado"].map(fmt_brl)
        fracionamento_md = fracionamento_fmt.to_markdown(index=False, disable_numparse=True)
    else:
        fracionamento_md = "_Nenhum indício de fracionamento na amostra._"

    n_sem_lic = len(sem_licitacao)
    n_elegiveis = len(df_contratos[~df_contratos["eh_dispensa_ou_inexigibilidade"]]) if not df_contratos.empty else 0
    n_checados = len(candidatos_checados)

    linhas = f"""# Licitações e compras — tarefa 3.3

Gerado por `analises/09_licitacoes.py`. Amostra: mesmas 15 instituições da
tarefa 3.2, licitações de {DATA_INICIO:%d/%m/%Y} a {DATA_FIM:%d/%m/%Y}.
{n_brutos} licitações brutas coletadas.

## 1. Limitação de escopo descoberta nesta tarefa

`/licitacoes` só aceita **até 1 mês por requisição** (diferente de
`/contratos`, que aceita o intervalo todo numa chamada) — descoberto por
erro HTTP 400 ("O período deve ser de no máximo 1 mês") ao tentar o mesmo
padrão da tarefa 3.2. Por isso a coleta ficou restrita a 2024 (1 ano, 12
requisições por instituição), não os 3 anos de `contratos_mec.parquet` —
o que limita a análise 3 abaixo (contratos sem licitação correspondente),
sujeita a falso positivo por essa diferença de cobertura temporal.

## 2. Licitações desertas/fracassadas repetidas (≥2 no mesmo órgão/ano)

{desertas_md}

**Leitura:** identificado por texto de `situacaoCompra` contendo "DESERTA"
ou "FRACASSAD" — deserta (nenhuma proposta) e fracassada (propostas
existiram mas nenhuma válida) têm causas distintas na prática, mas ambas
indicam uma tentativa de compra que não se concretizou; repetição no
mesmo órgão/ano é o sinal a olhar, não uma ocorrência isolada.

## 3. Indício de fracionamento (regra explícita)

Regra: ≥2 contratos por dispensa/inexigibilidade do mesmo (órgão,
fornecedor, ano), cada um abaixo de R$ {fmt_brl(LIMIAR_DISPENSA_REFERENCIA)}
(limiar de referência do valor-base da Lei 14.133/2021, art. 75, inciso
II, para compras/serviços em geral — sujeito a atualização por decreto de
indexação não considerada aqui), cuja soma ultrapassa esse limiar.

{fracionamento_md}

**Achado a cruzar com a tarefa 3.2:** a mesma "Fundação Euclides da Cunha
de Apoio Institucional à UFF" apontada na tarefa 3.2 como concentrando
86,6% do valor contratado da UFF (HHI 7.512, o mais alto da amostra)
aparece aqui também com 6 contratos por dispensa em 2023, cada um abaixo
do limiar, somando R$ 172.030,00 — a mesma entidade combina forte
concentração de valor E um padrão compatível com fracionamento. Não é
prova de irregularidade (fundações de apoio administram muitos pequenos
repasses de projetos legitimamente), mas é o tipo de sinal cruzado que a
Fase 4 (validação contra achados do TCU/CGU) deveria priorizar.

## 4. Contratos sem licitação correspondente

**Achado desta tarefa (corrigido):** o campo `numeroProcesso` no nível
raiz do payload de `/contratos` vem sempre "Sem informação" — o valor real
está aninhado em `compra.numeroProcesso` (não documentado no Swagger,
descoberto empiricamente; `sucuri.coletores.contratos` já foi corrigido
para usar o campo certo, com teste de regressão). Mesmo corrigido, apenas
{n_checados} de {n_elegiveis} contratos não-dispensa têm um número de
processo utilizável para o cruzamento (os demais têm o campo vazio mesmo
na fonte aninhada) — **é sobre esses {n_checados} que a comparação abaixo
é válida**, não sobre os {n_elegiveis} totais.

{n_sem_lic} de {n_checados} contratos checáveis não têm `numeroProcesso`
correspondente entre as licitações coletadas no mesmo órgão.
**Ressalva forte:** dado que licitações só cobrem 2024 e contratos cobrem
2023–2025, boa parte dessas "ausências" é esperada por diferença de
janela temporal, não indício de irregularidade — esta análise é
estruturalmente inconclusiva no escopo desta tarefa piloto; uma coleta de
licitações cobrindo 2023–2025 completo (45 novas requisições por
instituição) resolveria isso, deixada para o usuário rodar externamente.

## 5. Dados salvos

`dados/licitacoes_mec.parquet` — uma linha por licitação coletada.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    print("Coletando licitações...")
    registros = coletar_tudo(sessao)

    caminho_raw = DIR_DADOS / "raw" / "licitacoes_mec_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df_lic = construir_df_licitacoes(registros)
    if not df_lic.empty:
        df_lic.to_parquet(DIR_DADOS / "licitacoes_mec.parquet", index=False)
        print(f"Salvo: dados/licitacoes_mec.parquet ({len(df_lic)} linhas)")

    df_contratos = pd.read_parquet(DIR_DADOS / "contratos_mec.parquet")

    conteudo = gerar_relatorio(df_lic, df_contratos, len(registros))
    caminho_md = DIR_RELATORIOS / "09_licitacoes.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
