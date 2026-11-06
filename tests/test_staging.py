from decimal import Decimal

import pandas as pd
import pytest

from pipeline import db, staging


def _banco_com_raw(tmp_path, monkeypatch, colunas: dict[str, list]):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    db.gravar(con, "raw.teste", pd.DataFrame(colunas, dtype="object"))
    return con


def test_mapa_cobre_as_quatro_tabelas_com_contagem_de_colunas():
    assert staging.TABELAS == ("anuncios", "calendario", "avaliacoes", "bairros")
    assert len(staging.REGRAS["anuncios"]) == 90
    assert len(staging.REGRAS["calendario"]) == 5
    assert len(staging.REGRAS["avaliacoes"]) == 6
    assert len(staging.REGRAS["bairros"]) == 2


def test_chaves_existem_nas_regras():
    for tabela, chave in staging.CHAVES.items():
        nomes = [c for c, _ in staging.REGRAS[tabela]]
        assert all(k in nomes for k in chave)


def test_primeiro_invalido_devolve_none_quando_tudo_casa(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["t", "f", None]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") is None


def test_primeiro_invalido_devolve_o_valor_que_nao_casa(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["t", "T", "f"]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") == "T"


def test_price_com_virgula_de_milhar_converte(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"price": ["$1,234.56"]})
    assert con.execute(
        f"SELECT {staging.expressao_sql('price', 'decimal_preco')} FROM raw.teste"
    ).fetchall() == [(Decimal("1234.56"),)]


def test_price_com_tres_casas_decimais_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"price": ["$314.005"]})
    assert staging.primeiro_invalido(con, "raw.teste", "price", "decimal_preco") == "$314.005"


def test_boolean_inesperado_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["yes"]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") == "yes"


def test_texto_na_fica_texto(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["NA"]})
    assert con.execute(
        f"SELECT {staging.expressao_sql('x', 'texto')} FROM raw.teste"
    ).fetchall() == [("NA",)]


def test_converter_levanta_erro_com_tabela_coluna_e_exemplo(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"neighbourhood": ["a"]})
    monkeypatch.setattr(staging, "REGRAS", {"t": [("neighbourhood", "texto"), ("x", "boolean")]})
    db.gravar(con, "raw.t", pd.DataFrame({"neighbourhood": ["a"], "x": ["yes"]}, dtype="object"))
    with pytest.raises(staging.ErroConversao) as e:
        staging.converter(con, "t")
    assert (e.value.tabela, e.value.coluna, e.value.exemplo) == ("t", "x", "yes")


def test_linha_inteira_repetida_sai_e_e_contada(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": ["a", "a"]})
    assert staging.linhas_repetidas(con, "raw.teste") == 1


def test_null_igual_a_null_conta_como_repetida(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": [None, None]})
    assert staging.linhas_repetidas(con, "raw.teste") == 1


def test_mesma_chave_com_conteudo_diferente_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": ["a", "b"]})
    with pytest.raises(staging.ErroChaveConflitante) as e:
        staging.remover_repetidas(con, "raw.teste", chave=("id",))
    assert e.value.chave == ("1",)
    assert len(e.value.linhas) == 2


def _valor_valido(regra: str) -> str | None:
    return {
        "texto": "x",
        "bigint": "1",
        "integer": "1",
        "double": "1.5",
        "boolean": "t",
        "data": "2025-01-01",
        "decimal_preco": "$10.00",
    }[regra]


def _banco_com_quatro_raw(tmp_path, monkeypatch, invalido_em=None):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    for tabela in staging.TABELAS:
        colunas = {}
        for coluna, regra in staging.REGRAS[tabela]:
            valor = _valor_valido(regra)
            if invalido_em == (tabela, coluna, "maybe"):
                valor = "maybe"
            colunas[coluna] = [valor]
        db.gravar(con, f"raw.{tabela}", pd.DataFrame(colunas, dtype="object"))
    return con


def test_transformar_grava_quatro_tabelas_e_conta(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)
    resultado = staging.transformar(con)
    assert [t for t, _, _ in resultado] == list(staging.TABELAS)
    assert all(removidas == 0 for _, _, removidas in resultado)
    assert all(linhas == 1 for _, linhas, _ in resultado)


def test_falha_em_uma_tabela_nao_altera_nenhuma(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(
        tmp_path, monkeypatch, invalido_em=("calendario", "available", "maybe")
    )
    with pytest.raises(staging.ErroConversao):
        staging.transformar(con)
    tabelas = con.execute(
        "select table_name from information_schema.tables where table_schema='staging'"
    ).fetchall()
    assert tabelas == []


def test_falha_no_segundo_create_desfaz_o_primeiro(tmp_path, monkeypatch):
    # Validação passa para todas as tabelas; o CREATE de calendario falha
    # porque existe uma view com esse nome. anuncios, criada antes na mesma
    # transação, tem de ser desfeita (R4).
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute("CREATE VIEW staging.calendario AS SELECT 1 AS x")
    with pytest.raises(Exception):
        staging.transformar(con)
    tabelas = con.execute(
        "select table_name from information_schema.tables where table_schema='staging' order by 1"
    ).fetchall()
    assert tabelas == [("calendario",)]


def test_chave_composta_com_nulo_nao_conflita_e_repetida_e_contada(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    df = pd.DataFrame(
        {
            "listing_id": ["1", "1", None, None],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
            "available": ["t", "t", "t", "f"],
            "minimum_nights": ["2", "2", "1", "1"],
            "maximum_nights": ["30", "30", "2", "2"],
        },
        dtype="object",
    )
    db.gravar(con, "raw.calendario", df)
    # Uma linha repetida (listing 1, 2024-01-01); as duas linhas com chave nula
    # diferem em 'available' e não são conflito nem repetição.
    assert staging.remover_repetidas(con, "raw.calendario", chave=("listing_id", "date")) == 1


def test_duas_execucoes_dao_o_mesmo_resultado(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)
    primeira = staging.transformar(con)
    assert staging.transformar(con) == primeira


def test_faltantes_raw_lista_tabelas_ausentes(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    assert staging.faltantes_raw(con) == list(staging.TABELAS)
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)
    assert staging.faltantes_raw(con) == []


def _criar_quatro_raw_no_arquivo(caminho, invalido_em=None):
    # monkeypatch de db.caminho_banco já aponta para este caminho
    con = _banco_com_quatro_raw(caminho.parent, _MP, invalido_em)
    con.close()


class _MP:
    @staticmethod
    def setattr(obj, nome, valor):
        setattr(obj, nome, valor)


def _sem_schema_staging(caminho) -> bool:
    import duckdb

    con = duckdb.connect(str(caminho))
    try:
        return (
            con.execute(
                "select count(*) from information_schema.schemata where schema_name='staging'"
            ).fetchone()[0]
            == 0
        )
    finally:
        con.close()


def test_saida_uma_linha_por_tabela_e_total(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_raw_no_arquivo(tmp_path / "t.duckdb")
    assert staging.main() == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert linhas[-1].startswith("total")
    assert sum(1 for ln in linhas if ln.startswith("staging.")) == 4


def test_raw_faltando_lista_e_encerra_sem_criar(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    assert staging.main() == 1
    assert "pipeline.ingestao" in capsys.readouterr().out
    assert not (tmp_path / "t.duckdb").exists() or _sem_schema_staging(tmp_path / "t.duckdb")


def test_erro_de_conversao_imprime_tabela_coluna_e_exemplo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_raw_no_arquivo(
        tmp_path / "t.duckdb", invalido_em=("calendario", "available", "maybe")
    )
    assert staging.main() == 1
    saida = capsys.readouterr().out
    assert "calendario" in saida and "available" in saida and "maybe" in saida


@pytest.mark.parametrize(
    "regra,valor,exemplo",
    [
        ("data", "2024-02-30", "2024-02-30"),
        ("integer", "99999999999", "99999999999"),
        # o DuckDB cita o valor já sem "$" e ","
        ("decimal_preco", "$1,000,000,000.00", "1000000000.00"),
    ],
)
def test_converter_valor_que_passa_na_regex_mas_falha_no_cast_levanta_erro_conversao(
    tmp_path, monkeypatch, regra, valor, exemplo
):
    # Tabela raw construída com db.gravar, pois o helper _banco_com_raw só cria raw.teste.
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["a"]})
    monkeypatch.setattr(staging, "REGRAS", {"t": [("v", regra)]})
    db.gravar(con, "raw.t", pd.DataFrame({"v": [valor]}, dtype="object"))
    with pytest.raises(staging.ErroConversao) as e:
        staging.converter(con, "t")
    assert (e.value.tabela, e.value.coluna) == ("t", "v")
    assert exemplo in e.value.exemplo
