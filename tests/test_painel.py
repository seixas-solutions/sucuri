"""Teste de fumaça do painel Flask (tarefa 5.2): cada rota responde 200 e
contém um gráfico embutido. Pulado automaticamente quando o grupo de
dependências `painel` não está instalado (rodar com
`uv run --group painel pytest tests/test_painel.py`)."""

import pytest

flask = pytest.importorskip("flask", reason="grupo 'painel' não instalado")

from painel.app import app  # noqa: E402


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    with app.test_client() as cliente:
        yield cliente


@pytest.mark.parametrize("rota", ["/", "/instituicoes", "/anomalias", "/contratos", "/ibge"])
def test_rota_responde_com_grafico(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert b"data:image/png;base64," in resposta.data


def test_pagina_metodologia(cliente):
    resposta = cliente.get("/metodologia")
    assert resposta.status_code == 200
    assert "z-score robusto".encode() in resposta.data


def test_instituicao_via_query_string(cliente):
    resposta = cliente.get("/instituicoes?orgao=Universidade Federal Fluminense")
    assert resposta.status_code == 200
    assert "UFF".encode() in resposta.data


def test_instituicao_inexistente_404(cliente):
    assert cliente.get("/instituicoes?orgao=Nao Existe").status_code == 404


def test_filtro_min_sinais(cliente):
    resposta = cliente.get("/anomalias?min_sinais=3")
    assert resposta.status_code == 200
