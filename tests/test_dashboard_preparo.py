import importlib

import pandas as pd

from dashboard import preparo


def test_top_bairros_filtra_minimo_e_ordena():
    df = pd.DataFrame({"bairro": ["A", "B", "C"], "preco_mediano": [10, 30, 20],
                       "anuncios_com_preco": [100, 5, 100]})
    assert preparo.top_bairros(df, "preco_mediano")["bairro"].tolist() == ["C", "A"]


def test_top_bairros_usa_anuncios_e_limita_n():
    df = pd.DataFrame({"bairro": list("ABC"), "taxa_ocupacao_pct": [1.0, 3.0, 2.0],
                       "anuncios": [200, 200, 200]})
    assert preparo.top_bairros(df, "taxa_ocupacao_pct", n=2)["bairro"].tolist() == ["B", "C"]


def test_top_bairros_descarta_bairro_sem_valor():
    df = pd.DataFrame({"bairro": ["A", "B"], "preco_mediano": [None, 5.0],
                       "anuncios_com_preco": [100, 100]})
    assert preparo.top_bairros(df, "preco_mediano")["bairro"].tolist() == ["B"]


def test_tabela_completa_devolve_todos_os_bairros():
    df = pd.DataFrame({"bairro": list("ABC"), "preco_medio": [1.0, None, 3.0],
                       "anuncios_com_preco": [1, 5, 100]})
    assert len(preparo.tabela_completa(df, "preco_medio")) == 3


def test_serie_receita_soma_por_mes():
    df = pd.DataFrame({"mes": ["2026-09-01", "2026-09-01"], "receita_potencial": [1.0, 2.0]})
    assert preparo.serie_receita_mensal(df)["receita_potencial"].tolist() == [3.0]


def test_resumo_multi_host():
    df = pd.DataFrame({"anfitrioes": [10], "multi_host": [2], "fatia_multi_host_pct": [20.0],
                       "fatia_imoveis_multi_pct": [50.0]})
    assert preparo.resumo_multi_host(df) == {
        "anfitrioes": 10, "multi_host": 2, "fatia_pct": 20.0, "fatia_imoveis_pct": 50.0}


def test_df_vazio_nao_quebra():
    assert preparo.top_bairros(pd.DataFrame(columns=["bairro", "preco_mediano", "anuncios_com_preco"]), "preco_mediano").empty
    assert preparo.serie_receita_mensal(pd.DataFrame(columns=["mes", "receita_potencial"])).empty
    assert preparo.resumo_multi_host(pd.DataFrame()) == {}


def test_paginas_importam_e_tem_desenhar():
    for nome in ("anfitriao", "investidor"):
        modulo = importlib.import_module(f"dashboard.paginas.{nome}")
        assert callable(modulo.desenhar)


def test_diferenca_pct_inteiro_privado():
    df = pd.DataFrame({"tipo": ["Entire home/apt", "Private room"], "preco_mediano": [150.0, 100.0]})
    assert preparo.diferenca_pct_inteiro_privado(df) == 50.0
    assert preparo.diferenca_pct_inteiro_privado(pd.DataFrame()) is None
