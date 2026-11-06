import gzip

import duckdb
import pandas as pd
import pytest

from pipeline import db, ingestao


def test_cep_com_zero_fica_texto(tmp_path):
    p = tmp_path / "a.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write("cep\n01310-100\n")
    assert ingestao.ler_arquivo(p)["cep"].tolist() == ["01310-100"]


def test_textos_que_pandas_trata_como_nulo_ficam_texto(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("v\nNA\nnull\nN/A\nNaN\n", encoding="utf-8")
    assert ingestao.ler_arquivo(p)["v"].tolist() == ["NA", "null", "N/A", "NaN"]


def test_campo_vazio_e_aspas_vazias_viram_nulo(tmp_path):
    # Duas colunas: em CSV de uma coluna, linha em branco é ignorada pelo pandas.
    p = tmp_path / "a.csv"
    p.write_text('a,v\n1,\n2,""\n3,x\n', encoding="utf-8")
    assert ingestao.ler_arquivo(p)["v"].isna().tolist() == [True, True, False]


def test_utf8_com_acento_e_virgula_entre_aspas(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text('bairro,end\n"São Conrado","Rua A, 10"\n', encoding="utf-8")
    df = ingestao.ler_arquivo(p)
    assert df.loc[0, "bairro"] == "São Conrado"
    assert df.loc[0, "end"] == "Rua A, 10"


def test_todas_as_colunas_sao_texto(tmp_path):
    # Ruling: pandas>=3 usa dtype string por padrão; o que a spec exige é texto, não object.
    p = tmp_path / "a.csv"
    p.write_text("n,m\n1,2\n3,4\n", encoding="utf-8")
    df = ingestao.ler_arquivo(p)
    assert all(pd.api.types.is_string_dtype(d) for d in df.dtypes)


def test_faltantes_lista_os_que_faltam(tmp_path):
    (tmp_path / "listings.csv.gz").write_bytes(b"")
    assert ingestao.arquivos_faltantes(tmp_path) == [
        "calendar.csv.gz",
        "reviews.csv.gz",
        "neighbourhoods.csv",
    ]


def test_main_para_antes_de_conectar(tmp_path, capsys):
    chamadas = []

    def conectar_falso():
        chamadas.append(1)

    assert ingestao.main(pasta=tmp_path, conectar_fn=conectar_falso) == 1
    assert chamadas == []
    saida = capsys.readouterr().out
    assert "listings.csv.gz" in saida
    assert str(tmp_path) in saida


def _criar_quatro_arquivos_pequenos(pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in ("listings.csv.gz", "calendar.csv.gz", "reviews.csv.gz"):
        with gzip.open(pasta / nome, "wt", encoding="utf-8") as f:
            f.write("id,valor\n1,01310-100\n2,NA\n")
    (pasta / "neighbourhoods.csv").write_text("id,valor\n1,São Conrado\n", encoding="utf-8")


def test_formata_milhar_com_ponto():
    assert ingestao.formatar_contagem(1550922) == "1.550.922"
    assert ingestao.formatar_contagem(999) == "999"


def test_saida_uma_linha_por_tabela_e_total(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    assert ingestao.main(pasta=tmp_path / "raw") == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert len(linhas) == 5
    assert linhas[-1].startswith("total")


def test_duas_execucoes_imprimem_o_mesmo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    ingestao.main(pasta=tmp_path / "raw")
    primeira = capsys.readouterr().out
    ingestao.main(pasta=tmp_path / "raw")
    assert capsys.readouterr().out == primeira


def test_falha_no_meio_nao_deixa_parcial(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    (tmp_path / "raw" / "reviews.csv.gz").write_bytes(b"nao e gzip")  # terceira tabela do MAPA
    con = db.conectar()
    with pytest.raises(Exception):
        ingestao.ingerir(con, tmp_path / "raw")
    tabelas = con.execute(
        "select table_name from information_schema.tables where table_schema = 'raw'"
    ).fetchall()
    con.close()
    assert tabelas == []


def test_banco_em_uso_falha_com_mensagem_e_codigo_1(tmp_path, capsys):
    def conectar_em_uso():
        raise duckdb.Error("Could not set lock on file")

    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    assert ingestao.main(pasta=tmp_path / "raw", conectar_fn=conectar_em_uso) == 1
    assert "ui" in capsys.readouterr().out


def test_blocos_dao_mesmo_resultado_que_leitura_inteira(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    pasta = tmp_path / "raw"
    _criar_quatro_arquivos_pequenos(pasta)
    with gzip.open(pasta / "reviews.csv.gz", "wt", encoding="utf-8") as f:
        f.write("id,valor\n" + "".join(f"{i},01310-10{i}\n" for i in range(5)))

    monkeypatch.setattr(ingestao, "TAMANHO_BLOCO", 2)
    por_blocos = ingestao.ingerir(db.conectar(), pasta)
    monkeypatch.setattr(ingestao, "TAMANHO_BLOCO", 1_000_000)
    inteiro = ingestao.ingerir(db.conectar(), pasta)

    assert por_blocos == inteiro
    assert dict(por_blocos)["raw.avaliacoes"] == 5


def test_arquivo_so_com_cabecalho_cria_tabela_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    pasta = tmp_path / "raw"
    _criar_quatro_arquivos_pequenos(pasta)
    (pasta / "calendar.csv.gz").unlink()
    with gzip.open(pasta / "calendar.csv.gz", "wt", encoding="utf-8") as f:
        f.write("id,valor\n")
    con = db.conectar()
    resultado = dict(ingestao.ingerir(con, pasta))
    colunas = [r[0] for r in con.execute("describe raw.calendario").fetchall()]
    con.close()
    assert resultado["raw.calendario"] == 0
    assert colunas == ["id", "valor"]
