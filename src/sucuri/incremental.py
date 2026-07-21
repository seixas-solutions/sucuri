"""Recoleta incremental (tarefa 5.3): decidir quais anos recoletar e mesclar
os registros novos com o bruto da coleta anterior.

Princípio: um exercício orçamentário só é definitivo depois de encerrado.
O ano em que a coleta anterior rodou (carimbo `_YYYYMMDD` do arquivo bruto)
estava com o exercício em aberto, então esse ano — e qualquer ano posterior —
precisa ser recoletado; anos anteriores já fechados são reaproveitados do
bruto existente sem nenhuma requisição à API.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_PADRAO_RAW = re.compile(r"_raw_(\d{8})\.json$")


def raw_mais_recente(dir_raw: Path | str, nome_base: str) -> Path | None:
    """Retorna o arquivo bruto mais recente `<nome_base>_raw_YYYYMMDD.json`,
    ou `None` se não houver nenhum (primeira coleta)."""
    candidatos = [
        caminho
        for caminho in Path(dir_raw).glob(f"{nome_base}_raw_*.json")
        if _PADRAO_RAW.search(caminho.name)
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda c: _PADRAO_RAW.search(c.name).group(1))


def ano_do_carimbo(caminho: Path | str) -> int:
    """Extrai o ano do carimbo `_YYYYMMDD` do nome de um arquivo bruto."""
    m = _PADRAO_RAW.search(Path(caminho).name)
    if not m:
        raise ValueError(f"Nome sem carimbo '_raw_YYYYMMDD.json': {caminho}")
    return int(m.group(1)[:4])


def anos_presentes(registros: list[dict]) -> set[int]:
    """Anos distintos presentes em uma lista de registros brutos da API."""
    return {int(r["ano"]) for r in registros if r.get("ano") is not None}


def anos_a_coletar(
    anos_existentes: set[int], ano_inicio: int, ano_fim: int, ano_ultima_coleta: int
) -> list[int]:
    """Anos do intervalo que precisam ser (re)coletados: os ausentes do bruto
    existente e todos a partir do ano da última coleta (exercício que estava
    em aberto quando ela rodou — pode ter mudado desde então)."""
    return [
        ano
        for ano in range(ano_inicio, ano_fim + 1)
        if ano not in anos_existentes or ano >= ano_ultima_coleta
    ]


def mesclar_registros(
    registros_antigos: list[dict], registros_novos: list[dict], anos_recoletados: list[int]
) -> list[dict]:
    """Substitui, no bruto antigo, os anos recoletados pelos registros novos.

    Registros antigos de anos recoletados são descartados (mesmo que a
    recoleta tenha voltado vazia — a API é a fonte de verdade para esses
    anos); os demais são mantidos. Resultado ordenado por ano.
    """
    recoletados = set(anos_recoletados)
    mantidos = [
        r for r in registros_antigos if r.get("ano") is None or int(r["ano"]) not in recoletados
    ]
    return sorted(mantidos + list(registros_novos), key=lambda r: int(r.get("ano") or 0))


def carregar_registros(caminho: Path | str) -> list[dict]:
    """Lê a lista de registros de um arquivo bruto JSON."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))
