import duckdb
import pytest

from pipeline import db, marts


def test_lista_em_ordem_e_ignora_o_que_nao_e_arquivo_de_mart(tmp_path):
    (tmp_path / "02_b.sql").write_text("", encoding="utf-8")
    (tmp_path / "01_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "notas.txt").write_text("", encoding="utf-8")
    nomes = [p.name for p in marts.listar_arquivos(tmp_path)]
    assert nomes == ["01_a.sql", "02_b.sql"]


def test_lacuna_na_numeracao_para_antes_de_executar(tmp_path):
    (tmp_path / "01_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "03_c.sql").write_text("", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart):
        marts.listar_arquivos(tmp_path)


def test_numeracao_que_nao_comeca_em_01_para_antes_de_executar(tmp_path):
    (tmp_path / "02_b.sql").write_text("", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart):
        marts.listar_arquivos(tmp_path)


def test_arquivo_valido_devolve_o_nome_da_tabela(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text(
        "-- Mart: mart.teste\n\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\n",
        encoding="utf-8",
    )
    assert marts.verificar_arquivo(None, arq) == "mart.teste"


def test_duas_instrucoes_sao_recusadas(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text(
        "-- Mart: mart.teste\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\nSELECT 2;\n",
        encoding="utf-8",
    )
    with pytest.raises(marts.ErroArquivoMart) as e:
        marts.verificar_arquivo(None, arq)
    assert "01_teste.sql" in str(e.value)


def test_cabecalho_diferente_do_create_e_recusado(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text(
        "-- Mart: mart.outro\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\n",
        encoding="utf-8",
    )
    with pytest.raises(marts.ErroArquivoMart):
        marts.verificar_arquivo(None, arq)


def test_numero_repetido_para_antes_de_executar(tmp_path):
    (tmp_path / "01_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "01_b.sql").write_text("", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart):
        marts.listar_arquivos(tmp_path)


def test_executar_cria_a_tabela_e_conta_no_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    arq = tmp_path / "01_teste.sql"
    arq.write_text(
        "-- Mart: mart.teste\n"
        "CREATE OR REPLACE TABLE mart.teste AS SELECT * FROM (VALUES (1), (2), (3)) t(x);\n",
        encoding="utf-8",
    )
    assert marts.executar(con, arq) == ("mart.teste", 3)


def _banco_com_staging_minimo(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute("CREATE OR REPLACE TABLE staging.anuncios AS SELECT 1 AS id, 100 AS preco")
    for outra in ("calendario", "avaliacoes", "bairros"):
        con.execute(f"CREATE OR REPLACE TABLE staging.{outra} AS SELECT 1 AS id")
    return con


def _pasta_com_tres_marts_validos(tmp_path, quebrado=None, vazio=None):
    pasta = tmp_path / "marts"
    pasta.mkdir()
    for n in (1, 2, 3):
        nome = f"{n:02d}_t{n}.sql"
        origem = "staging.nao_existe" if nome == quebrado else "staging.anuncios"
        filtro = " WHERE 1 = 0" if nome == vazio else ""
        (pasta / nome).write_text(
            f"-- Mart: mart.t{n}\n"
            f"CREATE OR REPLACE TABLE mart.t{n} AS SELECT id, preco FROM {origem}{filtro};\n",
            encoding="utf-8",
        )
    return pasta


def test_todos_os_arquivos_geram_as_tabelas(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path)
    resultado = marts.executar_todos(con, pasta)
    assert [t for t, _ in resultado] == ["mart.t1", "mart.t2", "mart.t3"]


def test_falha_no_terceiro_arquivo_nao_cria_nenhuma(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path, quebrado="03_t3.sql")
    with pytest.raises(duckdb.CatalogException, match="nao_existe"):
        marts.executar_todos(con, pasta)
    tabelas = con.execute(
        "select table_name from information_schema.tables where table_schema='mart'"
    ).fetchall()
    assert tabelas == []
    esquemas = con.execute(
        "select schema_name from information_schema.schemata where schema_name='mart'"
    ).fetchall()
    assert esquemas == []


def test_duas_execucoes_dao_o_mesmo_resultado(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path)
    primeira = marts.executar_todos(con, pasta)
    assert marts.executar_todos(con, pasta) == primeira


def test_saida_uma_linha_por_mart_e_total(tmp_path, monkeypatch, capsys):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    con.close()
    assert marts.main(pasta=_pasta_com_tres_marts_validos(tmp_path)) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert linhas[-1].startswith("total")
    assert sum(1 for ln in linhas if ln.startswith("mart.")) == 3


def test_staging_faltando_manda_rodar_a_etapa_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    assert marts.main(pasta=_pasta_com_tres_marts_validos(tmp_path)) == 1
    assert "pipeline.staging" in capsys.readouterr().out
    con = db.conectar()
    esquemas = con.execute(
        "select schema_name from information_schema.schemata where schema_name='mart'"
    ).fetchall()
    assert esquemas == []


def test_mart_com_zero_linhas_e_valido(tmp_path, monkeypatch, capsys):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    con.close()
    pasta = _pasta_com_tres_marts_validos(tmp_path, vazio="02_t2.sql")
    assert marts.main(pasta=pasta) == 0
    assert "mart.t2" in capsys.readouterr().out


def test_erro_de_arquivo_devolve_1_com_mensagem(tmp_path, monkeypatch, capsys):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    con.close()
    pasta = _pasta_com_tres_marts_validos(tmp_path)
    (pasta / "05_x.sql").write_text("", encoding="utf-8")
    assert marts.main(pasta=pasta) == 1
    assert "05_x.sql" in capsys.readouterr().out
