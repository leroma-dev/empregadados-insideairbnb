import re

from dashboard import textos


def test_cada_grafico_tem_titulo_e_explicacao():
    for chave, texto in textos.TEXTOS.items():
        assert texto.titulo and texto.explicacao, chave


def test_explicacao_tem_no_maximo_tres_frases():
    for chave, texto in textos.TEXTOS.items():
        frases = [f for f in re.split(r"[.!?]+\s", texto.explicacao) if f.strip()]
        assert len(frases) <= 3, chave


def test_ocupacao_e_receita_trazem_as_ressalvas():
    assert "bloqueio" in textos.TEXTOS["ocupacao_bairro"].explicacao.lower()
    assert "estimat" in textos.TEXTOS["receita_mensal"].explicacao.lower()


def test_chaves_exatas():
    assert set(textos.TEXTOS) == {
        "preco_bairro", "ocupacao_bairro", "receita_mensal", "reviews_mensal",
        "sazonalidade", "inteiro_vs_privado", "superhost", "multi_host", "amenities",
    }


def test_receita_e_sazonalidade_citam_2026_incompleto():
    assert "2026" in textos.TEXTOS["receita_mensal"].explicacao


def test_reviews_e_sazonalidade_citam_2026_incompleto():
    for chave in ("reviews_mensal", "sazonalidade"):
        assert "2026" in textos.TEXTOS[chave].explicacao, chave
        assert "incompleto" in textos.TEXTOS[chave].explicacao, chave
