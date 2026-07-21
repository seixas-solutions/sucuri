"""Testes da recoleta incremental (tarefa 5.3 — sucuri.incremental)."""

import json

import pytest

from sucuri.incremental import (
    ano_do_carimbo,
    anos_a_coletar,
    anos_presentes,
    carregar_registros,
    mesclar_registros,
    raw_mais_recente,
)


# ---------------------------------------------------------------- anos_a_coletar
def test_sem_dados_existentes_coleta_tudo():
    assert anos_a_coletar(set(), 2014, 2017, 2016) == [2014, 2015, 2016, 2017]


def test_historico_completo_recoleta_so_ano_em_aberto():
    existentes = set(range(2014, 2027))
    assert anos_a_coletar(existentes, 2014, 2026, 2026) == [2026]


def test_virada_de_ano_recoleta_ano_parcial_anterior_e_novo():
    # Última coleta em jul/2026 (exercício 2026 em aberto); nova coleta em 2027:
    # 2026 precisa ser refeito e 2027 ainda não existe no bruto.
    existentes = set(range(2014, 2027))
    assert anos_a_coletar(existentes, 2014, 2027, 2026) == [2026, 2027]


def test_ano_ausente_no_meio_do_historico_entra_na_lista():
    existentes = {2014, 2015, 2017, 2018}
    assert anos_a_coletar(existentes, 2014, 2018, 2018) == [2016, 2018]


def test_intervalo_encerrado_antes_da_ultima_coleta_nao_recoleta_nada():
    existentes = set(range(2014, 2021))
    assert anos_a_coletar(existentes, 2014, 2020, 2026) == []


# ------------------------------------------------------------- mesclar_registros
def test_mescla_substitui_anos_recoletados_e_preserva_os_demais():
    antigos = [
        {"ano": 2024, "pago": "1,00"},
        {"ano": 2025, "pago": "2,00"},
        {"ano": 2026, "pago": "3,00"},
    ]
    novos = [{"ano": 2026, "pago": "9,00"}, {"ano": 2027, "pago": "4,00"}]
    resultado = mesclar_registros(antigos, novos, [2026, 2027])
    assert resultado == [
        {"ano": 2024, "pago": "1,00"},
        {"ano": 2025, "pago": "2,00"},
        {"ano": 2026, "pago": "9,00"},
        {"ano": 2027, "pago": "4,00"},
    ]


def test_mescla_descarta_ano_recoletado_mesmo_com_recoleta_vazia():
    # A API é a fonte de verdade: se o ano recoletado voltou sem registros,
    # os registros antigos dele não devem ressuscitar.
    antigos = [{"ano": 2026, "pago": "3,00"}]
    assert mesclar_registros(antigos, [], [2026]) == []


def test_mescla_ordena_por_ano_e_aceita_ano_como_texto():
    antigos = [{"ano": "2025", "pago": "2,00"}]
    novos = [{"ano": 2024, "pago": "1,00"}]
    resultado = mesclar_registros(antigos, novos, [2024])
    assert [int(r["ano"]) for r in resultado] == [2024, 2025]


def test_mescla_preserva_registro_sem_ano():
    antigos = [{"ano": None, "pago": "0,00"}, {"ano": 2025, "pago": "2,00"}]
    resultado = mesclar_registros(antigos, [], [2025])
    assert resultado == [{"ano": None, "pago": "0,00"}]


# ------------------------------------------------- raw_mais_recente / carimbos
def test_raw_mais_recente_escolhe_maior_carimbo(tmp_path):
    (tmp_path / "painel_raw_20250101.json").write_text("[]")
    (tmp_path / "painel_raw_20260706.json").write_text("[]")
    (tmp_path / "outro_raw_20270101.json").write_text("[]")  # outro nome_base
    caminho = raw_mais_recente(tmp_path, "painel")
    assert caminho is not None and caminho.name == "painel_raw_20260706.json"


def test_raw_mais_recente_sem_arquivos_retorna_none(tmp_path):
    assert raw_mais_recente(tmp_path, "painel") is None


def test_ano_do_carimbo():
    assert ano_do_carimbo("painel_raw_20260706.json") == 2026


def test_ano_do_carimbo_nome_invalido():
    with pytest.raises(ValueError):
        ano_do_carimbo("painel_sem_carimbo.json")


# ------------------------------------------------------------- anos_presentes
def test_anos_presentes_ignora_ano_nulo_e_converte_texto():
    registros = [{"ano": 2024}, {"ano": "2025"}, {"ano": None}, {"sem_ano": True}]
    assert anos_presentes(registros) == {2024, 2025}


def test_carregar_registros(tmp_path):
    caminho = tmp_path / "painel_raw_20260101.json"
    caminho.write_text(json.dumps([{"ano": 2024}]), encoding="utf-8")
    assert carregar_registros(caminho) == [{"ano": 2024}]
