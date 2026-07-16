#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarefa 2.2 do ROADMAP — Lei de Benford (primeiro e segundo dígitos).

Aplica o teste de Benford sobre `empenhado` e `pago` (valores nominais >
R$ 1.000 — a Lei de Benford é sobre dígitos de valores como reportados,
não deflacionados: deflação multiplica cada linha por um fator diferente
por ano, o que pode alterar dígitos sem relação com o fenômeno auditado):

  - Conjunto A completo (funcional-programático).
  - Conjunto B, separado por `tipo_instituicao` (comparação entre pares).

Gera `relatorios/03_benford.md` + figuras em `relatorios/figuras/`.

Uso:
    uv run python analises/03_benford.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sucuri.benford import AMOSTRA_MINIMA_CONCLUSIVA, aplicar_benford
from sucuri.graficos import PALETA_CATEGORICA, aplicar_estilo, salvar_figura

DIR_DADOS = Path("dados")
DIR_RELATORIOS = Path("relatorios")
DIR_FIGURAS = DIR_RELATORIOS / "figuras"
LIMIAR_VALOR = 1000.0


def carregar(nome: str) -> pd.DataFrame:
    df = pd.read_parquet(DIR_DADOS / f"{nome}_v2.parquet")
    return df[~df["ano_parcial"]]  # exclui ano parcial (execução ainda incompleta)


def grafico_observado_esperado(resultado: dict, titulo: str, caminho: Path) -> None:
    aplicar_estilo()
    fig, ax = plt.subplots(figsize=(7, 4))
    digitos = resultado["proporcao_observada"].index
    largura = 0.4
    x = range(len(digitos))
    ax.bar([i - largura / 2 for i in x], resultado["proporcao_observada"].values,
           width=largura, color=PALETA_CATEGORICA[0], label="Observado")
    ax.bar([i + largura / 2 for i in x], resultado["proporcao_esperada"].values,
           width=largura, color=PALETA_CATEGORICA[7], label="Esperado (Benford)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(d) for d in digitos])
    ax.set_xlabel("Dígito")
    ax.set_ylabel("Proporção")
    ax.set_title(titulo, fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    salvar_figura(fig, caminho)


def linha_resumo(rotulo: str, resultado: dict) -> dict:
    return {
        "grupo": rotulo,
        "n": resultado["n"],
        "amostra_suficiente": "sim" if resultado["amostra_suficiente"] else "NÃO (<300)",
        "chi2": round(resultado["chi2"], 1) if resultado["n"] else None,
        "p_valor": round(resultado["p_valor"], 4) if resultado["n"] else None,
        "MAD": round(resultado["mad"], 5) if resultado["n"] else None,
        "classificacao": resultado["classificacao"],
    }


def tabela_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def gerar_relatorio() -> str:
    df_a = carregar("despesas_ensino_superior")
    df_b = carregar("despesas_por_instituicao")

    resumos_a = []
    figs_a = []
    for coluna in ("empenhado", "pago"):
        valores = df_a.loc[df_a[coluna] > LIMIAR_VALOR, coluna]
        for posicao in ("primeiro", "segundo"):
            resultado = aplicar_benford(valores, posicao=posicao)
            rotulo = f"A · {coluna} · {posicao} dígito"
            resumos_a.append(linha_resumo(rotulo, resultado))
            if posicao == "primeiro":
                caminho = DIR_FIGURAS / f"05_benford_A_{coluna}.png"
                grafico_observado_esperado(
                    resultado, f"Conjunto A — {coluna} (1º dígito, n={resultado['n']})", caminho)
                figs_a.append((coluna, str(caminho)))

    resumos_b = []
    figs_b = []
    tipos = df_b["tipo_instituicao"].value_counts().index.tolist()
    for tipo in tipos:
        subset = df_b[df_b["tipo_instituicao"] == tipo]
        for coluna in ("empenhado", "pago"):
            valores = subset.loc[subset[coluna] > LIMIAR_VALOR, coluna]
            resultado = aplicar_benford(valores, posicao="primeiro")
            rotulo = f"B · {tipo} · {coluna} · 1º dígito"
            resumos_b.append(linha_resumo(rotulo, resultado))
            if coluna == "pago" and resultado["amostra_suficiente"]:
                caminho = DIR_FIGURAS / f"06_benford_B_{tipo.split()[0]}.png".replace("/", "-")
                grafico_observado_esperado(
                    resultado, f"Conjunto B — {tipo} — pago (1º dígito, n={resultado['n']})", caminho)
                figs_b.append((tipo, str(caminho)))

    df_resumo_a = pd.DataFrame(resumos_a)
    df_resumo_b = pd.DataFrame(resumos_b)

    figuras_a_md = "\n\n".join(
        f"![Benford A {c}]({Path(p).relative_to(DIR_RELATORIOS)})" for c, p in figs_a
    )
    figuras_b_md = "\n\n".join(
        f"![Benford B {t}]({Path(p).relative_to(DIR_RELATORIOS)})" for t, p in figs_b
    )

    n_grupos_pequenos_b = int((df_resumo_b["amostra_suficiente"] != "sim").sum())

    linhas = f"""# Lei de Benford — tarefa 2.2

Gerado por `analises/03_benford.py`. Base: `dados/*_v2.{{csv,parquet}}`,
excluindo o ano parcial (execução ainda incompleta distorceria a
distribuição de dígitos por truncamento artificial dos valores). Valores
**nominais** (`empenhado`/`pago`, não deflacionados — ver docstring do
script para a justificativa), filtrados para > R$ 1.000 (limiar do
ROADMAP; valores muito pequenos têm poucos algarismos significativos e
distorcem o teste).

Metodologia: qui-quadrado (conformidade estatística formal, sensível ao
tamanho da amostra) e MAD de Nigrini (classificação prática, menos
sensível ao tamanho da amostra — usada aqui como critério principal).
Amostras com menos de {AMOSTRA_MINIMA_CONCLUSIVA} valores são marcadas
como inconclusivas independentemente do resultado.

## 1. Conjunto A (funcional-programático)

{tabela_md(df_resumo_a)}

{figuras_a_md}

**Leitura — achado desta tarefa: a amostra do Conjunto A é insuficiente
para conclusão, nas quatro combinações.** Depois do filtro > R$ 1.000, só
restam {int(df_resumo_a["n"].min())}–{int(df_resumo_a["n"].max())} valores
por grupo (o Conjunto A tem ~81% de zeros nas colunas monetárias — ver
`relatorios/01_qualidade.md` — e a maior parte do que resta em cada
programa/ação é justamente pequena), abaixo do limiar de 300 adotado. O
primeiro dígito aparenta conformidade (MAD "aceitável") mas o segundo
dígito não ("Não conformidade") no mesmo par de colunas — direção
inconsistente entre os dois testes é o padrão típico de uma amostra
subdimensionada, não um sinal confiável de conformidade real. **Conclusão
desta seção: o Conjunto A, do jeito que está agregado hoje (uma linha por
ano×programa×ação), não tem volume suficiente para o teste de Benford ser
informativo.** Uma alternativa para uma iteração futura seria aplicar o
teste sobre lançamentos individuais de despesa (`/despesas/documentos`,
tarefa 3.1), que têm muito mais linhas que o painel agregado atual.

## 2. Conjunto B, por tipo de instituição

{tabela_md(df_resumo_b)}

{figuras_b_md}

**Leitura:** {n_grupos_pequenos_b} de {len(df_resumo_b)} combinações
tipo×coluna têm amostra insuficiente (<{AMOSTRA_MINIMA_CONCLUSIVA}) — a
maioria dos tipos de instituição (`CAPES`, `Fundo (FNDE/FIES)`, `Educação
Básica`, `Hospitalar (EBSERH)`) tem poucos órgãos e poucos anos, logo,
poucas dezenas de observações; **essas linhas são explicitamente
inconclusivas, não "não conformes"**, mesmo com qui-quadrado
estatisticamente significativo em vários casos — significância não supre
tamanho de amostra na classificação MAD adotada aqui.

Os dois grupos bem-dimensionados (`Universidade Federal`, n=791;
`Instituto/CEFET/Escola Técnica`, n=480) têm resultado conclusivo: **não
conformidade em ambos**, com o mesmo padrão nos dois — excesso do dígito 1
(observado 39,1% vs. 30,1% esperado em Universidade Federal) e déficit dos
dígitos 3–4 (9,6%/4,3% vs. 12,5%/9,7% esperado). A leitura mais provável
não é manipulação, e sim uma característica estrutural do Conjunto B: cada
linha é o **orçamento total anual de uma instituição do mesmo tipo**, uma
grandeza que tende a se concentrar numa faixa de magnitude relativamente
estreita (a maioria das universidades federais tem orçamento na casa das
centenas de milhões a poucos bilhões de reais) — Benford pressupõe valores
espalhados por várias ordens de grandeza, condição que totais
institucionais homogêneos violam por construção, não por fraude. Ver
gráficos para esses dois grupos.

## 3. Limitações do teste nesta aplicação

- Benford funciona melhor sobre valores de transações individuais
  cobrindo várias ordens de grandeza; aqui os "valores" são totais
  agregados (por ano×programa×ação ou por ano×órgão), não lançamentos
  contábeis individuais — desvios podem refletir a estrutura de agregação
  (ex.: poucos programas dominando o total, como visto na tarefa 2.1), não
  necessariamente manipulação.
- Não conformidade indica **prioridade para investigação com outras
  fontes** (Fase 3: documentos de despesa individuais, contratos), nunca
  conclusão de irregularidade por si só.
"""
    return linhas


def main() -> None:
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    conteudo = gerar_relatorio()
    caminho = DIR_RELATORIOS / "03_benford.md"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"Salvo: {caminho}")


if __name__ == "__main__":
    main()
