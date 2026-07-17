#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 3.5 do ROADMAP — Convênios e transferências.

Coleta `/convenios` com `codigoOrgao=26000` (Ministério da Educação, órgão
superior) — que já traz convênios de FNDE, CAPES e demais órgãos
subordinados na mesma consulta (achado empírico: um registro retornado
tinha `orgao.codigoSIAFI=26298`/FNDE sob `orgaoMaximo.codigo=26000`), não
sendo necessário iterar por sub-órgão como nas tarefas 3.2/3.3. Intervalo
2018–2025 (aceito numa única consulta paginada, como `/contratos`).

Uso:
    uv run python analises/11_convenios.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sucuri.api import ENV_PATH_PADRAO, carregar_chave_api, criar_sessao
from sucuri.coletores.convenios import (
    coletar_convenios,
    construir_df_convenios,
    convenentes_multiplos_inadimplentes,
    top_convenentes,
)

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DATA_INICIO = date(2018, 1, 1)
DATA_FIM = date(2025, 12, 31)


def fmt_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def gerar_relatorio(df, n_brutos: int) -> str:
    if df.empty:
        return "# Convênios e transferências — tarefa 3.5\n\nNenhum convênio coletado.\n"

    top20 = top_convenentes(df, n=20)
    top20_fmt = top20.copy()
    top20_fmt["valor_total"] = top20_fmt["valor_total"].map(fmt_brl)
    top20_fmt["convenenteNome"] = top20_fmt["convenenteNome"].str.slice(0, 45)
    top20_md = top20_fmt.to_markdown(index=False, disable_numparse=True)

    multiplos = convenentes_multiplos_inadimplentes(df)
    multiplos_md = multiplos.to_markdown(index=False) if not multiplos.empty else "_Nenhum convenente com ≥2 convênios inadimplentes na amostra._"

    n_inadimplentes = int(df["eh_inadimplente"].sum())
    pct_inadimplentes = n_inadimplentes / len(df)
    contagem_situacao = df["situacao"].value_counts()
    vocabulario_situacao = "; ".join(f"{s} (n={n})" for s, n in contagem_situacao.items())

    municipal = df[df["localidadeTipo"] == "Municipal"]
    valor_municipal_top10_pct = (
        municipal.groupby("convenenteCnpjCpf")["valor"].sum().sort_values(ascending=False).head(10).sum()
        / municipal["valor"].sum() if len(municipal) and municipal["valor"].sum() else 0.0
    )

    linhas = f"""# Convênios e transferências — tarefa 3.5

Gerado por `analises/11_convenios.py`. Concedente: Ministério da Educação
e órgãos vinculados (FNDE, CAPES etc., capturados automaticamente por
`codigoOrgao=26000`), {DATA_INICIO:%d/%m/%Y} a {DATA_FIM:%d/%m/%Y}.
{n_brutos} convênios brutos coletados.

## 1. Top 20 convenentes por valor total, com status de prestação de contas

{top20_md}

`n_inadimplentes` conta quantos dos convênios do próprio convenente estão
com situação "INADIMPLENTE" (qualquer variante do texto) — não é um
julgamento sobre o convenente como um todo, é a contagem literal de
convênios problemáticos.

## 2. Convenentes com múltiplos convênios inadimplentes (≥2)

{multiplos_md}

## 3. Panorama geral

- {n_inadimplentes} de {len(df)} convênios ({pct_inadimplentes:.1%}) estão
  com situação inadimplente.
- Convenentes municipais: top 10 por valor concentram
  {valor_municipal_top10_pct:.1%} do total liberado a convenentes
  municipais — sinal de concentração a cruzar com o porte populacional dos
  municípios (fora do escopo desta tarefa).

**Vocabulário de `situacao` conferido integralmente** (não só a palavra
"INADIMPLENTE"): {vocabulario_situacao}. Duas categorias próximas foram
deliberadamente **excluídas** da contagem de inadimplência por não
significarem inadimplência atual — "INADIMPLÊNCIA SUSPENSA" (a pendência
foi suspensa/resolvida) e "AGUARDANDO PRESTAÇÃO DE CONTAS" (prazo ainda
não vencido, não é atraso).

**Achado a cruzar com as tarefas 3.2/3.3:** a "Fundação Euclides da Cunha
de Apoio Institucional à UFF" — já apontada nas tarefas 3.2 (86,6% do
valor contratado da UFF, HHI mais alto da amostra) e 3.3 (padrão de
fracionamento, 6 dispensas somando R$ 172.030,00) — também recebeu
R$ 8.322.668,63 em convênio do MEC/FNDE/CAPES no período, situação
"CONCLUÍDO" (sem inadimplência registrada aqui). É a terceira tarefa
consecutiva em que essa entidade aparece como caso atípico por um critério
diferente — reforça a prioridade de investigação específica desta
fundação de apoio na Fase 4 (achados públicos do TCU/CGU), não como
acusação, mas como convergência de múltiplos sinais independentes.

## 4. Dados salvos

`dados/convenios_mec.parquet` — um registro por convênio coletado.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    (DIR_DADOS / "raw").mkdir(parents=True, exist_ok=True)

    chave = carregar_chave_api(ENV_PATH_PADRAO)
    sessao = criar_sessao(chave)

    print("Coletando convênios...")
    registros = coletar_convenios(sessao, DATA_INICIO, DATA_FIM)

    caminho_raw = DIR_DADOS / "raw" / "convenios_mec_raw_20260716.json"
    caminho_raw.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo bruto: {caminho_raw} ({len(registros)} registros)")

    df = construir_df_convenios(registros)
    if not df.empty:
        df.to_parquet(DIR_DADOS / "convenios_mec.parquet", index=False)
        print(f"Salvo: dados/convenios_mec.parquet ({len(df)} linhas)")

    conteudo = gerar_relatorio(df, len(registros))
    caminho_md = DIR_RELATORIOS / "11_convenios.md"
    caminho_md.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho_md}")


if __name__ == "__main__":
    main()
