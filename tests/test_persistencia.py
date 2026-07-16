"""Testes de sucuri.persistencia: detecção do ano de coleta pelo carimbo dos arquivos raw."""

import pytest

from sucuri.persistencia import detectar_ano_coleta


class TestDetectarAnoColeta:
    def test_detecta_ano_do_carimbo(self, tmp_path):
        (tmp_path / "despesas_ensino_superior_raw_20260706.json").write_text("[]")
        assert detectar_ano_coleta(tmp_path) == 2026

    def test_usa_carimbo_mais_recente_entre_varios_arquivos(self, tmp_path):
        (tmp_path / "despesas_ensino_superior_raw_20250115.json").write_text("[]")
        (tmp_path / "despesas_por_instituicao_raw_20260706.json").write_text("[]")
        assert detectar_ano_coleta(tmp_path) == 2026

    def test_diretorio_sem_arquivos_raw_levanta_erro(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            detectar_ano_coleta(tmp_path)

    def test_ignora_arquivos_fora_do_padrao(self, tmp_path):
        (tmp_path / "outro_arquivo.json").write_text("[]")
        with pytest.raises(FileNotFoundError):
            detectar_ano_coleta(tmp_path)
