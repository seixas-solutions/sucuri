"""Testes de sucuri.utils: conversão de valores e classificação de instituições."""

import math

import pandas as pd
import pytest

from sucuri.utils import brl_para_float, classificar_instituicao, razao_segura


class TestBrlParaFloat:
    def test_formato_brasileiro_com_milhar_e_decimal(self):
        assert brl_para_float("1.059.473.395,24") == 1059473395.24

    def test_formato_brasileiro_sem_milhar(self):
        assert brl_para_float("123,45") == 123.45

    def test_inteiro_sem_decimal(self):
        assert brl_para_float("1.000") == 1000.0

    def test_valor_none(self):
        assert brl_para_float(None) == 0.0

    def test_string_vazia(self):
        assert brl_para_float("") == 0.0

    def test_string_apenas_espacos(self):
        assert brl_para_float("   ") == 0.0

    def test_ja_numerico_float(self):
        assert brl_para_float(1234.5) == 1234.5

    def test_ja_numerico_int(self):
        assert brl_para_float(10) == 10.0

    def test_lixo_retorna_nan(self):
        assert math.isnan(brl_para_float("abc"))

    def test_negativo(self):
        assert brl_para_float("-1.234,56") == -1234.56


class TestRazaoSegura:
    def test_divisao_normal(self):
        num = pd.Series([10.0, 20.0])
        den = pd.Series([2.0, 4.0])
        resultado = razao_segura(num, den)
        assert resultado.tolist() == [5.0, 5.0]

    def test_denominador_zero_retorna_nan(self):
        num = pd.Series([10.0, 20.0])
        den = pd.Series([0.0, 4.0])
        resultado = razao_segura(num, den)
        assert math.isnan(resultado.iloc[0])
        assert resultado.iloc[1] == 5.0


class TestClassificarInstituicao:
    @pytest.mark.parametrize(
        "descricao,categoria_esperada",
        [
            ("UNIVERSIDADE FEDERAL DE MINAS GERAIS", "Universidade Federal"),
            ("HOSPITAL DE CLINICAS DE PORTO ALEGRE", "Hospitalar (EBSERH)"),
            ("INSTITUTO FEDERAL DE SAO PAULO", "Instituto/CEFET/Escola Técnica"),
            ("CENTRO FEDERAL DE EDUCACAO TECNOLOGICA", "Instituto/CEFET/Escola Técnica"),
            ("COORD DE APERFEICOAMENTO DE PESSOAL DE NIVEL SUPERIOR - CAPES",
             "CAPES"),
            ("FUNDO NACIONAL DE DESENVOLVIMENTO DA EDUCACAO", "Fundo (FNDE/FIES)"),
            ("COLEGIO PEDRO II", "Educação Básica"),
            ("MINISTERIO DA EDUCACAO - ADMINISTRACAO DIRETA", "Outros / Administração"),
        ],
    )
    def test_categorias(self, descricao, categoria_esperada):
        assert classificar_instituicao(descricao) == categoria_esperada

    def test_descricao_none(self):
        assert classificar_instituicao(None) == "Outros / Administração"

    def test_descricao_vazia(self):
        assert classificar_instituicao("") == "Outros / Administração"
