"""Testes de sucuri.benford: extração de dígitos e teste de Benford."""

import math

import pandas as pd
import pytest

from sucuri.benford import (
    aplicar_benford,
    classificar_mad,
    distribuicao_esperada,
    mad_nigrini,
    primeiro_digito,
    segundo_digito,
)


class TestPrimeiroDigito:
    def test_extrai_primeiro_digito_corretamente(self):
        serie = pd.Series([123.0, 5.0, 987654.0, 0.045])
        resultado = primeiro_digito(serie)
        assert resultado.tolist() == [1, 5, 9, 4]

    def test_descarta_valores_nao_positivos(self):
        serie = pd.Series([100.0, 0.0, -50.0, 200.0])
        resultado = primeiro_digito(serie)
        assert len(resultado) == 2

    def test_ignora_nan(self):
        serie = pd.Series([100.0, float("nan"), 200.0])
        resultado = primeiro_digito(serie)
        assert len(resultado) == 2


class TestSegundoDigito:
    def test_extrai_segundo_digito_corretamente(self):
        serie = pd.Series([123.0, 987654.0, 50.0])
        resultado = segundo_digito(serie)
        assert resultado.tolist() == [2, 8, 0]

    def test_valor_de_um_digito_e_descartado(self):
        # 5.0 normalizado é 5.0 -> não tem segundo dígito significativo real,
        # mas a implementação usa floor(5.0*10)%10 = 0 (convenção: dígito
        # implícito 0). Verificamos que não gera erro e o tamanho bate com a
        # entrada positiva.
        serie = pd.Series([5.0, 123.0])
        resultado = segundo_digito(serie)
        assert len(resultado) == 2


class TestDistribuicaoEsperada:
    def test_primeiro_digito_soma_um(self):
        dist = distribuicao_esperada("primeiro")
        assert dist.sum() == pytest.approx(1.0)
        assert list(dist.index) == list(range(1, 10))

    def test_primeiro_digito_e_decrescente(self):
        dist = distribuicao_esperada("primeiro")
        valores = dist.tolist()
        assert all(valores[i] > valores[i + 1] for i in range(len(valores) - 1))

    def test_digito_1_mais_provavel_que_9(self):
        dist = distribuicao_esperada("primeiro")
        assert dist.loc[1] == pytest.approx(0.30103, rel=1e-3)
        assert dist.loc[9] == pytest.approx(0.04576, rel=1e-3)

    def test_segundo_digito_soma_um(self):
        dist = distribuicao_esperada("segundo")
        assert dist.sum() == pytest.approx(1.0)
        assert list(dist.index) == list(range(0, 10))

    def test_posicao_invalida_levanta_erro(self):
        with pytest.raises(ValueError, match="primeiro"):
            distribuicao_esperada("terceiro")


class TestMadNigrini:
    def test_distribuicoes_identicas_mad_zero(self):
        p = pd.Series([0.3, 0.2, 0.5])
        assert mad_nigrini(p, p) == pytest.approx(0.0)

    def test_mad_calculado_corretamente(self):
        obs = pd.Series([0.4, 0.6])
        esp = pd.Series([0.3, 0.7])
        assert mad_nigrini(obs, esp) == pytest.approx(0.1)


class TestClassificarMad:
    def test_conformidade_proxima(self):
        assert classificar_mad(0.001, "primeiro") == "Conformidade próxima"

    def test_nao_conformidade(self):
        assert classificar_mad(0.05, "primeiro") == "Não conformidade"

    def test_limiares_diferentes_por_posicao(self):
        # 0.011 é "aceitável" no primeiro dígito (limite 0.012) mas
        # "marginal" no segundo (limite aceitável é 0.010, marginal 0.012)
        assert classificar_mad(0.011, "primeiro") == "Conformidade aceitável"
        assert classificar_mad(0.011, "segundo") == "Conformidade marginal"


class TestAplicarBenford:
    def test_serie_sintetica_seguindo_benford_conforma(self):
        import random
        random.seed(42)
        # Gera valores log-uniformes (~Benford) em várias ordens de grandeza.
        valores = [10 ** random.uniform(1, 6) for _ in range(5000)]
        resultado = aplicar_benford(pd.Series(valores), posicao="primeiro")
        assert resultado["amostra_suficiente"] is True
        assert resultado["mad"] < 0.012  # aceitável ou melhor

    def test_serie_uniforme_nao_conforma(self):
        import random
        random.seed(42)
        # Valores uniformes em escala linear violam fortemente Benford.
        valores = [random.uniform(500000, 599999) for _ in range(1000)]
        resultado = aplicar_benford(pd.Series(valores), posicao="primeiro")
        assert resultado["classificacao"] == "Não conformidade"

    def test_amostra_pequena_marcada_como_insuficiente(self):
        resultado = aplicar_benford(pd.Series([123.0, 456.0, 789.0]), posicao="primeiro")
        assert resultado["amostra_suficiente"] is False

    def test_amostra_vazia_nao_gera_erro(self):
        resultado = aplicar_benford(pd.Series([], dtype=float), posicao="primeiro")
        assert resultado["n"] == 0
        assert math.isnan(resultado["mad"])
        assert resultado["classificacao"] == "Sem dados"

    def test_chaves_do_resultado(self):
        resultado = aplicar_benford(pd.Series([123.0, 456.0]), posicao="segundo")
        for chave in ("n", "posicao", "contagem_observada", "proporcao_observada",
                      "proporcao_esperada", "chi2", "p_valor", "mad", "classificacao",
                      "amostra_suficiente"):
            assert chave in resultado
