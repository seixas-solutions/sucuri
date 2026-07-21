"""Utilidades genéricas: conversão de valores e classificação de instituições."""

from __future__ import annotations

import math

import pandas as pd


def brl_para_float(valor: str | float | None) -> float:
    """Converte '1.059.473.395,24' -> 1059473395.24. Vazio/None -> 0.0.

    Também trata dois formatos vistos nos endpoints da Fase 3
    (`/despesas/documentos` e afins, não usados pelos endpoints da Fase 0):
    valor negativo com espaço após o sinal (`'- 611,57'`) e traço solto
    como marcador de vazio/zero (`'-'`).
    """
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(" ", "")
    if not texto or texto == "-":
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return math.nan


def razao_segura(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Divisão elemento a elemento retornando NaN quando o denominador é 0."""
    den = denominador.where(denominador != 0)
    return numerador / den


# Sigla oficial/usual dos órgãos do Conjunto B (nome como vem da API do
# Portal da Transparência -> sigla). Cobre os ~115 órgãos do MEC; nomes fora
# do dicionário caem no próprio nome (ver `sigla_instituicao`).
SIGLAS_INSTITUICOES = {
    "Centro Federal de Educação Tecnológica Celso Suckow da Fonseca": "CEFET/RJ",
    "Centro Federal de Educação Tecnológica de Minas Gerais": "CEFET-MG",
    "Colégio Pedro II": "CPII",
    "Empresa Brasileira de Serviços Hospitalares": "EBSERH",
    "Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior": "CAPES",
    "Fundação Joaquim Nabuco": "FUNDAJ",
    "Fundação Universidade Federal da Grande Dourados": "UFGD",
    "Fundação Universidade Federal de Ciências da Saúde de Porto Alegre": "UFCSPA",
    "Fundação Universidade Federal de Pelotas": "UFPel",
    "Fundação Universidade Federal de Rondônia": "UNIR",
    "Fundação Universidade Federal de Sergipe": "UFS",
    "Fundação Universidade Federal de São Carlos": "UFSCar",
    "Fundação Universidade Federal de São João Del-Rei": "UFSJ",
    "Fundação Universidade Federal de Uberlândia": "UFU",
    "Fundação Universidade Federal do ABC": "UFABC",
    "Fundação Universidade Federal do Acre": "UFAC",
    "Fundação Universidade Federal do Amapá": "UNIFAP",
    "Fundação Universidade Federal do Mato Grosso": "UFMT",
    "Fundação Universidade Federal do Mato Grosso do Sul": "UFMS",
    "Fundação Universidade Federal do Pampa": "UNIPAMPA",
    "Fundação Universidade Federal do Piauí": "UFPI",
    "Fundação Universidade Federal do Tocantins": "UFT",
    "Fundação Universidade Federal do Vale do São Francisco": "UNIVASF",
    "Fundação Universidade de Brasília": "UnB",
    "Fundação Universidade do Amazonas": "UFAM",
    "Fundação Universidade do Maranhão": "UFMA",
    "Fundo Nacional de Desenvolvimento da Educação": "FNDE",
    "Hospital de Clínicas de Porto Alegre": "HCPA",
    "Instituto Federal de Educação, Ciência e Tecnologia Baiano": "IF Baiano",
    "Instituto Federal de Educação, Ciência e Tecnologia Catarinense": "IFC",
    "Instituto Federal de Educação, Ciência e Tecnologia Farroupilha": "IFFar",
    "Instituto Federal de Educação, Ciência e Tecnologia Fluminense": "IFF",
    "Instituto Federal de Educação, Ciência e Tecnologia Goiano": "IF Goiano",
    "Instituto Federal de Educação, Ciência e Tecnologia Sul-rio-grandense": "IFSul",
    "Instituto Federal de Educação, Ciência e Tecnologia da Bahia": "IFBA",
    "Instituto Federal de Educação, Ciência e Tecnologia da Paraíba": "IFPB",
    "Instituto Federal de Educação, Ciência e Tecnologia de Alagoas": "IFAL",
    "Instituto Federal de Educação, Ciência e Tecnologia de Brasília": "IFB",
    "Instituto Federal de Educação, Ciência e Tecnologia de Goiás": "IFG",
    "Instituto Federal de Educação, Ciência e Tecnologia de Minas Gerais": "IFMG",
    "Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco": "IFPE",
    "Instituto Federal de Educação, Ciência e Tecnologia de Rondônia": "IFRO",
    "Instituto Federal de Educação, Ciência e Tecnologia de Roraima": "IFRR",
    "Instituto Federal de Educação, Ciência e Tecnologia de Santa Catarina": "IFSC",
    "Instituto Federal de Educação, Ciência e Tecnologia de Sergipe": "IFS",
    "Instituto Federal de Educação, Ciência e Tecnologia de São Paulo": "IFSP",
    "Instituto Federal de Educação, Ciência e Tecnologia do Acre": "IFAC",
    "Instituto Federal de Educação, Ciência e Tecnologia do Amapá": "IFAP",
    "Instituto Federal de Educação, Ciência e Tecnologia do Amazonas": "IFAM",
    "Instituto Federal de Educação, Ciência e Tecnologia do Ceará": "IFCE",
    "Instituto Federal de Educação, Ciência e Tecnologia do Espírito Santo": "IFES",
    "Instituto Federal de Educação, Ciência e Tecnologia do Maranhão": "IFMA",
    "Instituto Federal de Educação, Ciência e Tecnologia do Mato Grosso": "IFMT",
    "Instituto Federal de Educação, Ciência e Tecnologia do Mato Grosso do Sul": "IFMS",
    "Instituto Federal de Educação, Ciência e Tecnologia do Norte de Minas Gerais": "IFNMG",
    "Instituto Federal de Educação, Ciência e Tecnologia do Pará": "IFPA",
    "Instituto Federal de Educação, Ciência e Tecnologia do Piauí": "IFPI",
    "Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte": "IFRN",
    "Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Sul": "IFRS",
    "Instituto Federal de Educação, Ciência e Tecnologia do Rio de Janeiro": "IFRJ",
    "Instituto Federal de Educação, Ciência e Tecnologia do Sertão de Pernambuco": "IF Sertão-PE",
    "Instituto Federal de Educação, Ciência e Tecnologia do Sudeste de Minas Gerais": "IF Sudeste MG",
    "Instituto Federal de Educação, Ciência e Tecnologia do Sul de Minas Gerais": "IFSULDEMINAS",
    "Instituto Federal de Educação, Ciência e Tecnologia do Tocantins": "IFTO",
    "Instituto Federal de Educação, Ciência e Tecnologia do Triângulo Mineiro": "IFTM",
    "Instituto Federal do Paraná": "IFPR",
    "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira": "INEP",
    "Ministério da Educação - Unidades com vínculo direto": "MEC (direto)",
    "Universidade Federal Fluminense": "UFF",
    "Universidade Federal Rural da Amazônia": "UFRA",
    "Universidade Federal Rural de Pernambuco": "UFRPE",
    "Universidade Federal Rural do Rio de Janeiro": "UFRRJ",
    "Universidade Federal Rural do Semi-Árido": "UFERSA",
    "Universidade Federal da Bahia": "UFBA",
    "Universidade Federal da Fronteira Sul": "UFFS",
    "Universidade Federal da Integração Latino-Americana": "UNILA",
    "Universidade Federal da Paraíba": "UFPB",
    "Universidade Federal de Alagoas": "UFAL",
    "Universidade Federal de Alfenas": "UNIFAL-MG",
    "Universidade Federal de Campina Grande": "UFCG",
    "Universidade Federal de Catalão": "UFCAT",
    "Universidade Federal de Goiás": "UFG",
    "Universidade Federal de Itajubá": "UNIFEI",
    "Universidade Federal de Jataí": "UFJ",
    "Universidade Federal de Juiz de Fora": "UFJF",
    "Universidade Federal de Lavras": "UFLA",
    "Universidade Federal de Minas Gerais": "UFMG",
    "Universidade Federal de Ouro Preto": "UFOP",
    "Universidade Federal de Pernambuco": "UFPE",
    "Universidade Federal de Rondonópolis": "UFR",
    "Universidade Federal de Roraima": "UFRR",
    "Universidade Federal de Santa Catarina": "UFSC",
    "Universidade Federal de Santa Maria": "UFSM",
    "Universidade Federal de São Paulo": "UNIFESP",
    "Universidade Federal de Viçosa": "UFV",
    "Universidade Federal do Agreste de Pernambuco": "UFAPE",
    "Universidade Federal do Cariri": "UFCA",
    "Universidade Federal do Ceará": "UFC",
    "Universidade Federal do Delta do Parnaíba": "UFDPar",
    "Universidade Federal do Espírito Santo": "UFES",
    "Universidade Federal do Estado do Rio de Janeiro": "UNIRIO",
    "Universidade Federal do Norte do Tocantins": "UFNT",
    "Universidade Federal do Oeste da Bahia": "UFOB",
    "Universidade Federal do Oeste do Pará": "UFOPA",
    "Universidade Federal do Paraná": "UFPR",
    "Universidade Federal do Pará": "UFPA",
    "Universidade Federal do Recôncavo da Bahia": "UFRB",
    "Universidade Federal do Rio Grande": "FURG",
    "Universidade Federal do Rio Grande do Norte": "UFRN",
    "Universidade Federal do Rio Grande do Sul": "UFRGS",
    "Universidade Federal do Rio de Janeiro": "UFRJ",
    "Universidade Federal do Sul da Bahia": "UFSB",
    "Universidade Federal do Sul e Sudeste do Pará": "UNIFESSPA",
    "Universidade Federal do Triângulo Mineiro": "UFTM",
    "Universidade Federal dos Vales do Jequitinhonha e Mucuri": "UFVJM",
    "Universidade Tecnológica Federal do Paraná": "UTFPR",
    "Universidade da Integração Internacional da Lusofonia Afro-Brasileira": "UNILAB",
}


def sigla_instituicao(nome: str | None) -> str:
    """Sigla oficial/usual do órgão do Conjunto B para rótulos de gráfico.

    Nome fora do dicionário (órgão novo na API) volta como veio — rótulo
    longo é preferível a inventar uma sigla errada.
    """
    if not nome:
        return ""
    return SIGLAS_INSTITUICOES.get(nome.strip(), nome.strip())


def zscore_robusto(serie: pd.Series) -> pd.Series:
    """Z-score robusto de uma amostra: 0,6745 × (x − mediana) / MAD.

    Mesma fórmula usada em `features.features_serie_temporal`, aqui para uma
    comparação transversal (ex.: UFs entre si num mesmo período). MAD zero
    (mais da metade dos valores idênticos) produz NaN, não erro.
    """
    mad = (serie - serie.median()).abs().median()
    if pd.isna(mad) or mad == 0:
        return pd.Series(pd.NA, index=serie.index, dtype="Float64")
    return 0.6745 * (serie - serie.median()) / mad


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
