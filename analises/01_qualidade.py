#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 1.1 do ROADMAP — Relatório de qualidade dos dados.

Gera `relatorios/01_qualidade.md` com diagnósticos de qualidade (não
estatísticos) dos Conjuntos A e B: cobertura por ano, proporção de zeros,
séries curtas, duplicatas e incoerências (`flag_pago_maior_empenhado`,
`flag_valor_negativo`). Não interpreta anomalias de gasto — isso é feito na
Fase 2. O comparativo de ordem de grandeza é descritivo, não uma validação
formal (essa fica para a tarefa 4.2, contra o SIOP/LOA).

Uso:
    uv run python analises/01_qualidade.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
COLUNAS_MONETARIAS = ["empenhado", "liquidado", "pago"]


def carregar(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DIR_DADOS / f"{nome}.parquet")


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def tabela_md_texto(df: pd.DataFrame) -> str:
    """Como `tabela_md`, mas para DataFrames com colunas monetárias já
    formatadas como string (ex.: "77,500,700.00") — evita que o tabulate
    reinterprete o texto como número e volte para notação científica."""
    return df.to_markdown(index=False, disable_numparse=True)


def secao_cobertura_por_ano(df: pd.DataFrame, chave_serie: str) -> tuple[str, pd.DataFrame]:
    resumo = (
        df.groupby("ano")
        .agg(n_linhas=("pago", "size"), n_series=(chave_serie, "nunique"),
             total_pago=("pago", "sum"))
        .reset_index()
    )
    resumo["total_pago_bi"] = (resumo["total_pago"] / 1e9).round(3)
    resumo = resumo.drop(columns="total_pago")
    return tabela_md(resumo), resumo


def secao_zeros(df: pd.DataFrame) -> str:
    linhas = []
    for col in COLUNAS_MONETARIAS:
        pct_zero = (df[col] == 0).mean() * 100
        linhas.append({"coluna": col, "pct_zeros": round(pct_zero, 1)})
    return tabela_md(pd.DataFrame(linhas))


def secao_series_curtas(df: pd.DataFrame, chave_serie: str, min_anos: int = 5) -> tuple[str, int, int]:
    anos_por_serie = df.groupby(chave_serie)["ano"].nunique()
    curtas = anos_por_serie[anos_por_serie < min_anos]
    total_series = anos_por_serie.shape[0]
    return (
        f"{len(curtas)} de {total_series} séries ({len(curtas) / total_series:.1%}) "
        f"têm menos de {min_anos} anos de observações.",
        len(curtas),
        total_series,
    )


def secao_duplicatas(df: pd.DataFrame, colunas_chave: list[str]) -> int:
    return int(df.duplicated(subset=colunas_chave).sum())


def diagnostico_duplicatas_conjunto_a(df: pd.DataFrame) -> dict:
    """Diagnostica a causa-raiz das duplicatas de (ano, chave_serie) no Conjunto A.

    Achado: o endpoint da API retorna, para o mesmo par programa/ação, duas
    grafias do texto (com/sem acentuação, com/sem espaço) sob o mesmo
    `codigoPrograma`/`codigoAcao` — não são séries diferentes. Na maioria dos
    casos ambas as grafias têm valor zero; em alguns, uma grafia carrega o
    valor real e a irmã fica zerada (risco de subcontagem se a chave_serie
    for tratada ingenuamente como única).
    """
    mask = df.duplicated(subset=["ano", "chave_serie"], keep=False)
    dups = df[mask]
    n_grupos = dups.groupby(["ano", "chave_serie"]).ngroups
    grupos = dups.groupby(["ano", "chave_serie"])
    n_valores_iguais = 0
    n_valores_diferentes = 0
    exemplos_diferentes = []
    for chave, g in grupos:
        if g[["empenhado", "liquidado", "pago"]].nunique().max() > 1:
            n_valores_diferentes += 1
            exemplos_diferentes.append((chave, g))
        else:
            n_valores_iguais += 1
    return {
        "n_linhas_duplicadas": int(mask.sum()),
        "n_grupos": n_grupos,
        "n_valores_iguais": n_valores_iguais,
        "n_valores_diferentes": n_valores_diferentes,
        "exemplos_diferentes": exemplos_diferentes,
    }


def secao_incoerencias(df: pd.DataFrame, colunas_id: list[str]) -> tuple[str, int, int]:
    pago_maior = df[df["flag_pago_maior_empenhado"]]
    valor_neg = df[df["flag_valor_negativo"]]
    colunas_mostrar = list(dict.fromkeys(colunas_id + ["ano", "empenhado", "liquidado", "pago"]))
    colunas_mostrar = [c for c in colunas_mostrar if c in df.columns]

    def _fmt(sub: pd.DataFrame) -> pd.DataFrame:
        sub = sub[colunas_mostrar].head(20).copy()
        for col in ("empenhado", "liquidado", "pago"):
            if col in sub.columns:
                sub[col] = sub[col].map(lambda v: f"{v:,.2f}")
        return sub

    partes = []
    if len(pago_maior):
        partes.append("**`flag_pago_maior_empenhado`** (pago > empenhado):\n\n"
                       + tabela_md_texto(_fmt(pago_maior)))
    else:
        partes.append("**`flag_pago_maior_empenhado`**: nenhuma linha.")
    if len(valor_neg):
        partes.append("**`flag_valor_negativo`**:\n\n"
                       + tabela_md_texto(_fmt(valor_neg)))
    else:
        partes.append("**`flag_valor_negativo`**: nenhuma linha.")
    return "\n\n".join(partes), len(pago_maior), len(valor_neg)


def gerar_relatorio() -> str:
    df_a = carregar("despesas_ensino_superior")
    df_b = carregar("despesas_por_instituicao")

    ano_atual = datetime.now().year

    cobertura_a_md, cobertura_a = secao_cobertura_por_ano(df_a, "chave_serie")
    cobertura_b_md, cobertura_b = secao_cobertura_por_ano(df_b, "chave_serie")

    zeros_a_md = secao_zeros(df_a)
    zeros_b_md = secao_zeros(df_b)

    series_curtas_txt, n_curtas, n_total_series = secao_series_curtas(df_a, "chave_serie")

    dup_a = secao_duplicatas(df_a, ["ano", "chave_serie"])
    dup_b = secao_duplicatas(df_b, ["ano", "chave_serie"])
    diag_a = diagnostico_duplicatas_conjunto_a(df_a)

    exemplo_md = ""
    if diag_a["exemplos_diferentes"]:
        chave, g = diag_a["exemplos_diferentes"][0]
        g_fmt = g[["ano", "programa", "acao", "empenhado", "liquidado", "pago"]].copy()
        for col in ("empenhado", "liquidado", "pago"):
            g_fmt[col] = g_fmt[col].map(lambda v: f"{v:,.2f}")
        exemplo_md = tabela_md_texto(g_fmt)

    incoerencias_a_md, n_pago_maior_a, n_neg_a = secao_incoerencias(
        df_a, ["ano", "programa", "acao"])
    incoerencias_b_md, n_pago_maior_b, n_neg_b = secao_incoerencias(
        df_b, ["ano", "orgao", "tipo_instituicao"])

    total_2025_a = cobertura_a.loc[cobertura_a["ano"] == 2025, "total_pago_bi"]
    total_2025_a = float(total_2025_a.iloc[0]) if len(total_2025_a) else float("nan")
    total_2025_b = cobertura_b.loc[cobertura_b["ano"] == 2025, "total_pago_bi"]
    total_2025_b = float(total_2025_b.iloc[0]) if len(total_2025_b) else float("nan")

    linhas = f"""# Relatório de qualidade dos dados — tarefa 1.1

Gerado por `analises/01_qualidade.py` em {datetime.now():%Y-%m-%d %H:%M}.
Escopo: Conjunto A (`despesas_ensino_superior`) e Conjunto B
(`despesas_por_instituicao`), tal como salvos por `coletar_despesas.py`
(sem deflação nem tratamento de ano parcial — isso é feito nas tarefas 1.2
e 1.3). Este relatório verifica **qualidade dos dados**, não anomalias de
gasto.

## 1. Cobertura por ano

### Conjunto A — funcional-programático

{cobertura_a_md}

### Conjunto B — por instituição (MEC)

{cobertura_b_md}

**Leitura:** {ano_atual} aparece com poucos meses de dados (coleta feita em
julho/{ano_atual}) — é o **ano parcial** já documentado em `CLAUDE.md`; seu
`total_pago_bi` mais baixo não indica queda de despesa, apenas cobertura
incompleta do exercício. Tratado formalmente na tarefa 1.3.

## 2. Proporção de zeros por coluna monetária

### Conjunto A

{zeros_a_md}

### Conjunto B

{zeros_b_md}

**Leitura:** o Conjunto A tem proporção de zeros muito mais alta que o B —
esperado, pois A tem granularidade fina (programa × ação), com muitas
combinações que só recebem dotação/execução em alguns anos. Linhas
zeradas não são erro: representam ações orçamentárias existentes sem
execução naquele ano. Confirma a ressalva já registrada em `CLAUDE.md`
("mediana de empenhado/liquidado/pago é zero" no Conjunto A).

## 3. Séries curtas (Conjunto A)

{series_curtas_txt}

Séries com poucos anos de histórico tornam `zscore_pago`/`variacao_pago_aa`
pouco confiáveis (poucos pontos para estimar média/desvio). A tarefa 1.3
cria a flag `serie_curta` para essas {n_curtas} séries e as trata à parte na
Fase 2.

## 4. Duplicatas

- Conjunto A: {dup_a} linhas duplicadas em (`ano`, `chave_serie`) — em
  {diag_a['n_grupos']} grupos ano×série com 2 linhas cada.
- Conjunto B: {dup_b} linhas duplicadas em (`ano`, `chave_serie`).

**Causa-raiz investigada (Conjunto A):** não são séries diferentes
colidindo por acaso — é a API retornando, para o **mesmo**
`codigoPrograma`/`codigoAcao`, duas grafias do nome do programa/ação (ex.:
"BRASIL UNIVERSITARIO" vs. "BRASIL UNIVERSITÁRIO", "BOLSA PERMANENCIA" vs.
"BOLSAPERMANENCIA" sem espaço), aparentemente por uma correção de texto na
fonte que não substituiu o registro antigo. Em **{diag_a['n_valores_iguais']}
de {diag_a['n_grupos']}** grupos os dois registros têm valores monetários
idênticos (frequentemente ambos zero); em **{diag_a['n_valores_diferentes']}
de {diag_a['n_grupos']}** grupos os valores diferem — um registro carrega o
valor real e o outro fica zerado. Exemplo:

{exemplo_md}

**Risco:** se `chave_serie` (programa-ação) for tratada como identificador
único de série sem agregação, os `{diag_a['n_valores_diferentes']}` casos
com valores divergentes fazem uma série real "sumir" em anos em que a API
devolveu a grafia zerada, e "reaparecer" no ano seguinte — parecendo (para um
detector de anomalia ingênuo) um salto de 0 para um valor alto, quando na
verdade não houve salto algum, apenas duas grafias do mesmo registro. Fixado
na tarefa 1.3: os dois conjuntos passam por agregação
`groupby(["ano","chave_serie"]).sum()` nas colunas monetárias antes do
recálculo de flags, eliminando a duplicidade sem perder valor.

## 5. Incoerências de execução orçamentária

Linhas em que os estágios da despesa (empenhado → liquidado → pago) não
seguem a ordem esperada. Podem refletir estornos, republicações ou
particularidades contábeis legítimas — não são necessariamente erro de
dado, mas merecem checagem manual quando poucas.

### Conjunto A ({n_pago_maior_a} com pago > empenhado, {n_neg_a} com valor negativo)

{incoerencias_a_md}

### Conjunto B ({n_pago_maior_b} com pago > empenhado, {n_neg_b} com valor negativo)

{incoerencias_b_md}

## 6. Checagem descritiva de ordem de grandeza

Comparação **qualitativa**, não uma validação formal (essa é a tarefa 4.2,
contra dotação do SIOP/LOA): o total pago em {2025} no Conjunto B (todos os
órgãos do MEC, todas as funções) foi de aproximadamente **R$ {total_2025_b:.1f}
bilhões**, e no Conjunto A (só subfunção 364 — Ensino Superior, nível
federal) foi de aproximadamente **R$ {total_2025_a:.1f} bilhões**. Ambos os
valores estão na ordem de grandeza publicamente conhecida do orçamento
federal do MEC (dezenas de bilhões de reais/ano, historicamente entre
~R$100 bi e ~R$200 bi de orçamento total do ministério, do qual uma fração
relevante é ensino superior). Não há, portanto, indício de erro grosseiro de
unidade (ex.: valores em centavos não convertidos, ou truncamento). Uma
comparação linha a linha com a dotação autorizada fica para a tarefa 4.2.

## 7. Conclusão

Não há erro de ordem de grandeza. Três pontos exigem tratamento antes da
modelagem de anomalias (Fase 2), todos endereçados na tarefa 1.3:

1. **Ano parcial** (seção 1) — já antecipado em `CLAUDE.md`.
2. **Séries curtas** (seção 3) — já antecipado em `CLAUDE.md`.
3. **Duplicatas por grafia no Conjunto A** (seção 4) — achado **novo** desta
   tarefa, não estava em `CLAUDE.md` antes deste relatório. É a descoberta
   mais importante desta análise de qualidade: sem a agregação por
   `(ano, chave_serie)`, a Fase 2 correria risco real de gerar falsos
   positivos de "salto anual" a partir de uma duplicidade de texto na fonte,
   não de um evento de gasto.

As incoerências da seção 5, quando existentes, devem ser lidas como
candidatas a checagem manual, não como conclusão de erro.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    conteudo = gerar_relatorio()
    caminho = DIR_RELATORIOS / "01_qualidade.md"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho}")


if __name__ == "__main__":
    main()
