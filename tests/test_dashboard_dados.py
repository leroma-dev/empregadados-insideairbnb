import duckdb
import pytest

from dashboard import dados


def test_carregar_do_parquet(tmp_path):
    duckdb.connect().execute(
        f"COPY (SELECT 1 AS x) TO '{tmp_path / 'preco_bairro.parquet'}' (FORMAT parquet)"
    )
    df = dados.carregar("preco_bairro", origem_escolhida="publicacao", pasta=tmp_path)
    assert df["x"].tolist() == [1]


def test_nome_fora_dos_marts_levanta(tmp_path):
    with pytest.raises(ValueError):
        dados.carregar("nao_existe", origem_escolhida="publicacao", pasta=tmp_path)


def test_banco_em_uso_vira_erro_claro(tmp_path, monkeypatch):
    # simula o lock do explorador: a conexão de leitura falha
    monkeypatch.setattr(dados, "_conectar_leitura", lambda p: (_ for _ in ()).throw(duckdb.IOException("Could not set lock")))
    with pytest.raises(dados.ErroOrigem) as erro:
        dados.carregar("preco_bairro", origem_escolhida="banco", caminho_banco=tmp_path / "x.duckdb")
    assert "explorador" in str(erro.value)
    assert str(tmp_path) not in str(erro.value)


def test_arquivo_ausente_cita_so_o_nome(tmp_path):
    with pytest.raises(dados.ErroOrigem) as erro:
        dados.carregar("preco_bairro", origem_escolhida="publicacao", pasta=tmp_path)
    mensagem = str(erro.value)
    assert "preco_bairro.parquet" in mensagem
    assert "data/publicacao" in mensagem
    assert str(tmp_path) not in mensagem


def test_origem_publicacao_nao_abre_banco(tmp_path, monkeypatch):
    duckdb.connect().execute(
        f"COPY (SELECT 1 AS x) TO '{tmp_path / 'preco_bairro.parquet'}' (FORMAT parquet)"
    )
    chamadas = []
    monkeypatch.setattr(dados, "_conectar_leitura", lambda p: chamadas.append(p))
    dados.carregar("preco_bairro", origem_escolhida="publicacao", pasta=tmp_path)
    assert chamadas == []


def _preparar(tmp_path, monkeypatch, com_banco, com_atualizacao=True, env=None):
    banco = tmp_path / "x.duckdb"
    if com_banco:
        banco.write_text("", encoding="utf-8")
    if com_atualizacao:
        (tmp_path / "atualizacao.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dados, "PASTA_PUBLICACAO", tmp_path)
    monkeypatch.setattr(dados, "caminho_banco", lambda: banco)
    if env is None:
        monkeypatch.delenv("DASHBOARD_ORIGEM", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_ORIGEM", env)


def test_origem_banco_quando_ha_duckdb_mesmo_com_atualizacao(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, com_banco=True)
    assert dados.origem() == "banco"


def test_origem_publicacao_sem_duckdb(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, com_banco=False)
    assert dados.origem() == "publicacao"


def test_origem_variavel_de_ambiente_tem_prioridade(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, com_banco=True, env="publicacao")
    assert dados.origem() == "publicacao"
    _preparar(tmp_path, monkeypatch, com_banco=False, env="banco")
    assert dados.origem() == "banco"


def test_origem_valor_invalido_levanta(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, com_banco=True, env="outro")
    with pytest.raises(ValueError):
        dados.origem()
