"""Testes das utilidades de cruzamento com o IBGE (sucuri.ibge) e do
z-score robusto transversal (sucuri.utils.zscore_robusto)."""

import pandas as pd
import pytest

from sucuri.ibge import extrair_series, extrair_uf, interpolar_anos_faltantes
from sucuri.utils import zscore_robusto

PAYLOAD_EXEMPLO = [
    {
        "id": "9324",
        "variavel": "População residente estimada",
        "unidade": "Pessoas",
        "resultados": [
            {
                "classificacoes": [],
                "series": [
                    {
                        "localidade": {"id": "1", "nivel": {"id": "N1"}, "nome": "Brasil"},
                        "serie": {"2024": "212583750", "2025": "213421037"},
                    },
                    {
                        "localidade": {"id": "35", "nivel": {"id": "N3"}, "nome": "São Paulo"},
                        "serie": {"2024": "45973194", "2025": "-"},
                    },
                ],
            }
        ],
    }
]


# ---------------------------------------------------------------- extrair_series
def test_extrair_series_achata_payload():
    df = extrair_series(PAYLOAD_EXEMPLO)
    assert len(df) == 4
    brasil_2025 = df[(df["localidade"] == "Brasil") & (df["ano"] == 2025)]
    assert brasil_2025["valor"].iloc[0] == 213421037


def test_extrair_series_marcador_nao_numerico_vira_nan():
    df = extrair_series(PAYLOAD_EXEMPLO)
    sp_2025 = df[(df["localidade"] == "São Paulo") & (df["ano"] == 2025)]
    assert pd.isna(sp_2025["valor"].iloc[0])


def test_extrair_series_payload_vazio():
    df = extrair_series([])
    assert df.empty and list(df.columns) == ["localidade_id", "localidade", "ano", "valor"]


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
