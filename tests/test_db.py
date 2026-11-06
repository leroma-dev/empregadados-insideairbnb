import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_caminho_banco_independe_da_pasta(tmp_path):
    saida = subprocess.run(
        [sys.executable, "-c", "from pipeline.db import caminho_banco; print(caminho_banco())"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert Path(saida) == RAIZ / "data" / "insideairbnb.duckdb"


def test_importar_nao_cria_banco(tmp_path):
    alvo = RAIZ / "data" / "insideairbnb.duckdb"
    antes = alvo.exists()
    subprocess.run([sys.executable, "-c", "import pipeline.db"], cwd=tmp_path, check=True)
    assert alvo.exists() == antes


import pandas as pd  # noqa: E402

from pipeline import db  # noqa: E402


def _banco_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")


def test_conectar_cria_arquivo_e_schema_raw(tmp_path, monkeypatch):
    _banco_temporario(tmp_path, monkeypatch)
    con = db.conectar()
    schemas = [
        r[0] for r in con.execute("select schema_name from information_schema.schemata").fetchall()
    ]
    con.close()
    assert (tmp_path / "t.duckdb").exists()
    assert "raw" in schemas


def test_gravar_devolve_contagem_do_banco(tmp_path, monkeypatch):
    _banco_temporario(tmp_path, monkeypatch)
    con = db.conectar()
    df = pd.DataFrame({"a": ["1", "2", "3"]})
    assert db.gravar(con, "raw.teste", df) == 3
    assert db.gravar(con, "raw.teste", df) == 3
    con.close()


def test_gravar_preserva_cep_com_zero_e_textos_nulos(tmp_path, monkeypatch):
    _banco_temporario(tmp_path, monkeypatch)
    con = db.conectar()
    df = pd.DataFrame({"cep": ["01310-100", None], "na": ["NA", "x"]})
    db.gravar(con, "raw.teste", df)
    assert con.execute("select cep from raw.teste order by na").fetchall() == [
        ("01310-100",),
        (None,),
    ]
    assert con.execute("select na from raw.teste order by na").fetchall() == [("NA",), ("x",)]
    con.close()


def test_conectar_limita_memoria_do_duckdb(tmp_path, monkeypatch):
    _banco_temporario(tmp_path, monkeypatch)
    con = db.conectar()
    limite = con.execute("select current_setting('memory_limit')").fetchall()[0][0]
    con.close()
    numero, unidade = limite.split()
    assert unidade in ("GiB", "GB")
    assert 1.0 < float(numero) <= 2.0
