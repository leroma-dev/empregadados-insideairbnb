"""Blocos de tela reaproveitados pelas duas paginas."""

import streamlit as st

from dashboard.dados_ui import carregar_cache
from dashboard.preparo import tabela_completa, top_bairros
from dashboard.textos import TEXTOS

MINIMO_ANUNCIOS = 100


def cabecalho(chave: str, nota: str = "") -> None:
    st.subheader(TEXTOS[chave].titulo)
    st.caption(f"{TEXTOS[chave].explicacao} {nota}".strip())


def grafico_bairros(chave: str, mart: str, coluna: str) -> None:
    """Top 15 em barras horizontais (so bairros com anuncios suficientes) e tabela com todos."""
    cabecalho(chave, f"Gráfico: bairros com {MINIMO_ANUNCIOS} ou mais anúncios.")
    completo = carregar_cache(mart)
    top = top_bairros(completo, coluna, minimo_anuncios=MINIMO_ANUNCIOS)
    if top.empty:
        st.info("sem dados")
        return
    st.bar_chart(top, x=coluna, y="bairro", horizontal=True, sort=f"-{coluna}")
    st.caption("Tabela com todos os bairros:")
    st.dataframe(tabela_completa(completo, coluna))
