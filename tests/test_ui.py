import ast
from pathlib import Path

import pytest

from ui import ui


def test_sem_banco_encerra_sem_criar_arquivo(tmp_path, capsys):
    alvo = tmp_path / "x.duckdb"
    with pytest.raises(SystemExit) as e:
        ui.verificar_banco(alvo)
    assert e.value.code == 1
    assert not alvo.exists()
    assert "ingest" in capsys.readouterr().out.lower()


def test_ui_nao_importa_pipeline():
    arvore = ast.parse(Path(ui.__file__).read_text(encoding="utf-8"))
    importados = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)}
    importados |= {a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and m.startswith("pipeline") for m in importados)


def test_sequencia_de_chamadas(tmp_path, monkeypatch):
    banco = tmp_path / "x.duckdb"
    banco.write_bytes(b"")
    chamadas = []

    class Falsa:
        def execute(self, sql):
            chamadas.append(sql)

        def close(self):
            chamadas.append("close")

    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Falsa())

    def ctrl_c():
        raise KeyboardInterrupt

    assert ui.main(caminho=banco, esperar=ctrl_c) == 0
    assert chamadas == ["INSTALL ui; LOAD ui;", "CALL start_ui()", "close"]


def test_ctrl_c_fecha_e_sai_sem_excecao(tmp_path, monkeypatch):
    banco = tmp_path / "x.duckdb"
    banco.write_bytes(b"")
    fechou = []

    class Falsa:
        def execute(self, sql):
            pass

        def close(self):
            fechou.append(True)

    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Falsa())

    def ctrl_c():
        raise KeyboardInterrupt

    assert ui.main(caminho=banco, esperar=ctrl_c) == 0
    assert fechou == [True]


def test_erro_do_duckdb_devolve_1(tmp_path, monkeypatch, capsys):
    banco = tmp_path / "x.duckdb"
    banco.write_bytes(b"")

    class Falsa:
        def execute(self, sql):
            raise ui.duckdb.Error("porta ocupada")

        def close(self):
            pass

    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Falsa())
    assert ui.main(caminho=banco, esperar=lambda: None) == 1
    assert "porta ocupada" in capsys.readouterr().out
