import json

import duckdb

from pipeline import publicacao
from dashboard.dados import MARTS

MARTS_TESTE = ("preco_bairro", "ocupacao_bairro")


def _banco_com_marts_minimos(tmp_path, monkeypatch, sem=None):
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute("CREATE SCHEMA mart")
    for nome in MARTS:
        if nome != sem:
            con.execute(f"CREATE TABLE mart.{nome} AS SELECT * FROM range(2) t(x)")
    return con


def test_exporta_parquet_e_atualizacao(tmp_path, monkeypatch):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch)
    resultado = publicacao.exportar(con, tmp_path / "pub", MARTS_TESTE)
    assert all(n == 2 for _, n in resultado)
    assert (tmp_path / "pub" / "preco_bairro.parquet").exists()
    dados = json.loads((tmp_path / "pub" / "atualizacao.json").read_text())
    assert dados["marts"]["preco_bairro"] == 2
    assert dados["gerado_em"].endswith("+00:00")
    assert sorted(p.name for p in (tmp_path / "pub").iterdir()) == [
        "atualizacao.json", "ocupacao_bairro.parquet", "preco_bairro.parquet",
    ]


def test_mart_faltando_nao_grava_nada(tmp_path, monkeypatch):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch, sem="multi_host")
    assert publicacao.main(conectar_fn=lambda: con, pasta=tmp_path / "pub") == 1
    assert not (tmp_path / "pub").exists() or not list((tmp_path / "pub").iterdir())


def test_main_exporta_todos(tmp_path, monkeypatch, capsys):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch)
    assert publicacao.main(conectar_fn=lambda: con, pasta=tmp_path / "pub") == 0
    assert len(list((tmp_path / "pub").glob("*.parquet"))) == 9
    assert "total" in capsys.readouterr().out


def test_falha_no_meio_nao_deixa_arquivos(tmp_path, monkeypatch):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch, sem="ocupacao_bairro")
    try:
        publicacao.exportar(con, tmp_path / "pub", MARTS_TESTE)
    except duckdb.Error:
        pass
    assert not (tmp_path / "pub").exists()
    assert list(tmp_path.glob(".pub*")) == []
