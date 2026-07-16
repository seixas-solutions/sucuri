"""Persistência dos conjuntos de dados tratados e brutos."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger("sucuri.persistencia")

_PADRAO_CARIMBO_RAW = re.compile(r"_raw_(\d{8})\.json$")


def detectar_ano_coleta(dir_raw: Path | str = Path("dados/raw")) -> int:
    """Detecta o ano em que a coleta mais recente foi executada, a partir do
    carimbo `_YYYYMMDD` nos nomes de arquivo em `dados/raw/*.json`.

    Esse é o "ano parcial" da tarefa 1.3: a coleta captura o exercício
    orçamentário corrente até a data em que rodou, então o ano do carimbo
    tende a estar com o exercício incompleto (ver ressalva em CLAUDE.md).
    """
    dir_raw = Path(dir_raw)
    carimbos = []
    for caminho in dir_raw.glob("*_raw_*.json"):
        m = _PADRAO_CARIMBO_RAW.search(caminho.name)
        if m:
            carimbos.append(m.group(1))
    if not carimbos:
        raise FileNotFoundError(
            f"Nenhum arquivo '*_raw_YYYYMMDD.json' encontrado em '{dir_raw}' "
            "para detectar o ano da coleta."
        )
    carimbo_mais_recente = max(carimbos)
    return int(carimbo_mais_recente[:4])


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

## Conjuntos derivados da Fase 1 (qualidade, deflação, ano parcial)

As tabelas acima descrevem `despesas_ensino_superior.*` e
`despesas_por_instituicao.*` — a saída original de `coletar_despesas.py`
(tarefa 0.1). A Fase 1 do ROADMAP adiciona dois conjuntos derivados, cada
um em cima do anterior. **Use `*_v2` para qualquer análise de anomalia — os
dois primeiros existem apenas como estágios intermediários do pipeline.**

### `*_real.{csv,parquet}` (tarefa 1.2 — `analises/01b_deflacionar.py`)
Mesmas colunas de A/B, mais `empenhado_real`, `liquidado_real`, `pago_real`:
valores deflacionados pelo IPCA (fonte:
`dados/externos/ipca_anual.csv`, obtido por `analises/00_baixar_ipca.py`),
em R$ do último ano com os 12 meses de IPCA disponíveis (ano-base). As
colunas `taxa_*`/`zscore_*`/`flag_*` deste arquivo AINDA são as originais
(nominais, sem dedup, sem exclusão de ano parcial) — não usar para análise
de anomalia; servem só de estágio intermediário para a tarefa 1.3.

### `*_v2.{csv,parquet}` (tarefa 1.3 — `analises/01c_ano_parcial_e_flags.py`)
Conjunto recomendado para a Fase 2. Diferenças em relação ao `_real`:
- **Deduplicado** (Conjunto A): linhas de `(ano, chave_serie)` duplicadas
  por grafia divergente do mesmo programa/ação na fonte (ver
  `relatorios/01_qualidade.md`, seção 4) foram agregadas por soma.
- **`ano_parcial`** (bool): `True` no ano em que a coleta foi executada
  (detectado pelo carimbo de `dados/raw/*.json` —
  `sucuri.persistencia.detectar_ano_coleta`), tipicamente com exercício
  orçamentário incompleto.
- **`serie_curta`** (bool, só A): `True` para séries (`chave_serie`) com
  menos de 5 anos distintos de observação.
- `variacao_pago_aa`, `zscore_pago`, `zscore_robusto_pago` e (só B)
  `zscore_pago_entre_pares` foram **recalculados com base em `pago_real`**
  (não mais `pago` nominal) e **excluindo** da base estatística as linhas
  com `ano_parcial=True` ou `serie_curta=True`. Essas linhas ficam com
  `NaN` nas métricas e `False` nas flags derivadas — não são avaliadas
  quanto a anomalia por falta de uma base de comparação confiável (mas
  `empenhado`/`liquidado`/`pago`/`*_real` continuam preenchidos
  normalmente).
- `flag_anomalia` foi recalculada por `consolidar_flags` sobre o conjunto
  final de flags acima.
"""


def resumir(df: pd.DataFrame, nome: str) -> None:
    if df.empty:
        return
    anos = f"{int(df['ano'].min())}–{int(df['ano'].max())}"
    total = f"{df['pago'].sum():,.2f}"
    n_anom = int(df["flag_anomalia"].sum())
    log.info("[%s] %d registros | anos %s | total pago R$ %s | %d possíveis anomalias",
              nome, len(df), anos, total, n_anom)
