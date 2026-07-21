"""Testes das utilidades de cruzamento com o IBGE (sucuri.ibge) e dos
utilitários transversais de sucuri.utils (zscore_robusto, sigla_instituicao)."""

import pandas as pd
import pytest

from sucuri.ibge import extrair_uf, interpolar_anos_faltantes, normalizar_sidra
from sucuri.utils import sigla_instituicao, zscore_robusto


def montar_retorno_sidra(colunas_dimensao: dict[str, tuple[str, list[str]]],
                         valores: list[str]) -> pd.DataFrame:
    """Monta um DataFrame com a estrutura do sidrapy: linha 0 = rótulos das
    colunas, demais linhas = dados. `colunas_dimensao` mapeia o par D#C/D#N
    para (rótulo, lista de valores da coluna N)."""
    n = len(valores)
    dados = {"NC": ["Nível Territorial (Código)"] + ["3"] * n, "V": ["Valor"] + valores}
    for codigo_n, (rotulo, valores_n) in colunas_dimensao.items():
        codigo_c = codigo_n.replace("N", "C")
        dados[codigo_c] = [f"{rotulo} (Código)"] + [str(i) for i in range(1, n + 1)]
        dados[codigo_n] = [rotulo] + valores_n
    return pd.DataFrame(dados)


# --------------------------------------------------------------- normalizar_sidra
def test_normalizar_sidra_identifica_dimensoes_pelos_rotulos():
    bruto = montar_retorno_sidra(
        {
            "D1N": ("Unidade da Federação", ["Rondônia", "Rondônia"]),
            "D2N": ("Ano", ["2014", "2015"]),
            "D3N": ("Variável", ["PIB", "PIB"]),
        },
        ["100", "110"],
    )
    df = normalizar_sidra(bruto)
    assert list(df.columns) == ["localidade_id", "localidade", "ano", "valor"]
    assert df["ano"].tolist() == [2014, 2015]
    assert df["valor"].tolist() == [100.0, 110.0]
    assert df["localidade"].tolist() == ["Rondônia", "Rondônia"]


def test_normalizar_sidra_ordem_de_dimensoes_diferente():
    # A ordem dos pares D# varia por tabela — o ano pode vir em D1.
    bruto = montar_retorno_sidra(
        {
            "D1N": ("Ano", ["2020"]),
            "D2N": ("Brasil", ["Brasil"]),
            "D3N": ("Variável", ["População"]),
        },
        ["212000000"],
    )
    df = normalizar_sidra(bruto)
    assert df["localidade"].iloc[0] == "Brasil"
    assert df["ano"].iloc[0] == 2020


def test_normalizar_sidra_marcador_nao_numerico_vira_nan():
    bruto = montar_retorno_sidra(
        {
            "D1N": ("Unidade da Federação", ["São Paulo", "São Paulo"]),
            "D2N": ("Ano", ["2024", "2025"]),
            "D3N": ("Variável", ["Pop", "Pop"]),
        },
        ["45973194", "-"],
    )
    df = normalizar_sidra(bruto)
    assert df["valor"].iloc[0] == 45973194.0
    assert pd.isna(df["valor"].iloc[1])


def test_normalizar_sidra_vazio():
    df = normalizar_sidra(pd.DataFrame())
    assert df.empty and list(df.columns) == ["localidade_id", "localidade", "ano", "valor"]


def test_normalizar_sidra_sem_dimensao_ano_levanta_erro():
    bruto = montar_retorno_sidra(
        {"D1N": ("Unidade da Federação", ["Acre"]), "D2N": ("Variável", ["Pop"])},
        ["800000"],
    )
    with pytest.raises(ValueError):
        normalizar_sidra(bruto)


# --------------------------------------------------------------- sigla_instituicao
def test_sigla_instituicao_universidades_conhecidas():
    assert sigla_instituicao("Universidade Federal Fluminense") == "UFF"
    assert sigla_instituicao("Fundação Universidade Federal do Vale do São Francisco") == "UNIVASF"
    assert sigla_instituicao("Universidade Federal do Estado do Rio de Janeiro") == "UNIRIO"
    assert sigla_instituicao("Universidade Federal do Rio Grande") == "FURG"


def test_sigla_instituicao_nao_universidades():
    assert sigla_instituicao("Empresa Brasileira de Serviços Hospitalares") == "EBSERH"
    assert (
        sigla_instituicao("Fundação Coordenação de Aperfeiçoamento de Pessoal de Nível Superior")
        == "CAPES"
    )


def test_sigla_instituicao_nome_desconhecido_volta_como_veio():
    assert sigla_instituicao("Órgão Novo Qualquer") == "Órgão Novo Qualquer"


def test_sigla_instituicao_nulo_ou_vazio():
    assert sigla_instituicao(None) == ""
    assert sigla_instituicao("") == ""


# ------------------------------------------------------ interpolar_anos_faltantes
def test_interpolacao_linear_no_meio_da_serie():
    df = pd.DataFrame(
        {
            "localidade_id": ["1"] * 2,
            "localidade": ["Brasil"] * 2,
            "ano": [2021, 2024],
            "valor": [100.0, 130.0],
        }
    )
    completo = interpolar_anos_faltantes(df, [2021, 2022, 2023, 2024])
    por_ano = completo.set_index("ano")
    assert por_ano.loc[2022, "valor"] == pytest.approx(110.0)
    assert por_ano.loc[2023, "valor"] == pytest.approx(120.0)
    assert bool(por_ano.loc[2022, "interpolado"]) is True
    assert bool(por_ano.loc[2021, "interpolado"]) is False


def test_interpolacao_nao_extrapola_fora_do_intervalo():
    df = pd.DataFrame(
        {"localidade_id": ["1"], "localidade": ["Brasil"], "ano": [2020], "valor": [100.0]}
    )
    completo = interpolar_anos_faltantes(df, [2019, 2020, 2021])
    por_ano = completo.set_index("ano")
    assert pd.isna(por_ano.loc[2019, "valor"]) and pd.isna(por_ano.loc[2021, "valor"])


def test_interpolacao_sem_lacunas_nao_altera_valores():
    df = pd.DataFrame(
        {
            "localidade_id": ["1"] * 3,
            "localidade": ["Brasil"] * 3,
            "ano": [2020, 2021, 2022],
            "valor": [100.0, 105.0, 110.0],
        }
    )
    completo = interpolar_anos_faltantes(df, [2020, 2021, 2022])
    assert completo["valor"].tolist() == [100.0, 105.0, 110.0]
    assert not completo["interpolado"].any()


def test_interpolacao_independente_por_localidade():
    df = pd.DataFrame(
        {
            "localidade_id": ["11", "11", "35", "35"],
            "localidade": ["Rondônia", "Rondônia", "São Paulo", "São Paulo"],
            "ano": [2020, 2022, 2020, 2022],
            "valor": [10.0, 20.0, 100.0, 200.0],
        }
    )
    completo = interpolar_anos_faltantes(df, [2020, 2021, 2022])
    ro = completo[(completo["localidade_id"] == "11") & (completo["ano"] == 2021)]
    sp = completo[(completo["localidade_id"] == "35") & (completo["ano"] == 2021)]
    assert ro["valor"].iloc[0] == pytest.approx(15.0)
    assert sp["valor"].iloc[0] == pytest.approx(150.0)


# -------------------------------------------------------------------- extrair_uf
def test_extrair_uf_formato_municipio():
    assert extrair_uf("BOM JESUS - PI") == "PI"


def test_extrair_uf_municipio_com_hifen_no_nome():
    assert extrair_uf("MOGI-MIRIM - SP") == "SP"


def test_extrair_uf_formato_estado():
    assert extrair_uf("RIO GRANDE DO NORTE (UF)") == "RN"
    assert extrair_uf("ESPÍRITO SANTO (UF)") == "ES"


def test_extrair_uf_agregados_sem_uf_retornam_none():
    for texto in ("Nacional", "Nordeste", "Centro-Oeste", "MÚLTIPLO"):
        assert extrair_uf(texto) is None


def test_extrair_uf_entrada_nula_ou_vazia():
    assert extrair_uf(None) is None
    assert extrair_uf("") is None


def test_extrair_uf_sigla_desconhecida_retorna_none():
    assert extrair_uf("CIDADE FICTICIA - XX") is None


# ---------------------------------------------------------------- zscore_robusto
def test_zscore_robusto_valores_conhecidos():
    serie = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    z = zscore_robusto(serie)
    # mediana=3, MAD=1 -> z do outlier = 0.6745 * 97
    assert z.iloc[4] == pytest.approx(0.6745 * 97)
    assert z.iloc[2] == pytest.approx(0.0)


def test_zscore_robusto_mad_zero_produz_nan():
    serie = pd.Series([5.0, 5.0, 5.0, 5.0])
    assert zscore_robusto(serie).isna().all()


def test_zscore_robusto_serie_vazia():
    serie = pd.Series([], dtype=float)
    assert zscore_robusto(serie).empty
