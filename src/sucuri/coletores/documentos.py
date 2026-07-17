"""Coletor de despesas por documento individual — tarefa 3.1 do ROADMAP.

Endpoint `/despesas/documentos`: único jeito, via API, de obter despesa
recortada por **órgão E subfunção ao mesmo tempo** (o painel usado desde a
Fase 0, `/despesas/por-orgao`, só filtra por órgão; `/despesas/por-funcional-programatica`
só filtra por subfunção — nenhum dos dois cruza as duas dimensões).

Duas limitações empíricas descobertas ao explorar a API (não documentadas
de forma óbvia no Swagger) — ver `relatorios/07_despesas_documentos.md`:

  1. O endpoint exige filtrar por **um dia por vez** (`dataEmissao`) e por
     `fase` (1=empenho, 2=liquidação, 3=pagamento) — não aceita intervalo
     de datas. Cobrir um ano inteiro de uma instituição custa até
     365 dias × 3 fases = 1.095 requisições.
  2. O filtro de instituição é por `unidadeGestora` (código SIAFI de UG,
     6 dígitos) — **não** é o mesmo código de `codigoOrgao` (5 dígitos)
     usado em `/despesas/por-orgao` e no Conjunto B deste projeto, e não
     há endpoint público desta API para converter um no outro. A UG
     correta de cada instituição precisa vir de outra fonte (ex.: os
     arquivos de download em lote do portal, que trazem `codigoOrgao` e
     `codigoUg` na mesma linha — ver EXTERNAL.md, item E2).
"""

from __future__ import annotations

from datetime import date, timedelta

from sucuri.api import ENDPOINT_DESPESAS_DOCUMENTOS, coletar_paginado

FASES = {1: "empenho", 2: "liquidacao", 3: "pagamento"}


def coletar_documentos_periodo(
    sessao,
    unidade_gestora: str,
    data_inicio: date,
    data_fim: date,
    fases: tuple[int, ...] = (1, 2, 3),
) -> list[dict]:
    """Coleta documentos de despesa de uma UG, dia a dia, para as `fases`
    pedidas, entre `data_inicio` e `data_fim` (inclusive). Uma requisição
    HTTP por (dia, fase) com resultado não vazio; dias sem movimento não
    geram erro, só retornam lista vazia (comportamento normal da API, não
    tratado como falha).
    """
    registros: list[dict] = []
    dia = data_inicio
    while dia <= data_fim:
        data_str = dia.strftime("%d/%m/%Y")
        for fase in fases:
            pagina = coletar_paginado(
                sessao, ENDPOINT_DESPESAS_DOCUMENTOS,
                {"unidadeGestora": unidade_gestora, "dataEmissao": data_str, "fase": fase},
                f"documentos UG={unidade_gestora} {data_str} fase={FASES.get(fase, fase)}",
            )
            for r in pagina:
                r["_fase_consultada"] = fase
            registros.extend(pagina)
        dia += timedelta(days=1)
    return registros
