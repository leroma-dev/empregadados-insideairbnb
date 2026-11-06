"""Pagina do anfitriao: so desenha; os numeros vem de preparo."""

import streamlit as st

from dashboard.dados_ui import carregar_cache as carregar
from dashboard.graficos import cabecalho as _cabecalho, grafico_bairros
from dashboard.preparo import diferenca_pct_inteiro_privado


def desenhar() -> None:
    grafico_bairros("preco_bairro", "preco_bairro", "preco_medio")

    _cabecalho("inteiro_vs_privado")
    tipos = carregar("inteiro_vs_privado")
    if tipos.empty:
        st.info("sem dados")
    else:
        st.bar_chart(tipos, x="tipo", y=["preco_mediano", "preco_medio"], stack=False)
        dif = diferenca_pct_inteiro_privado(tipos)
        if dif is not None:
            st.caption(f"Diferença: o preço mediano do imóvel inteiro é {dif:.0f}% maior que o do quarto privado.")

    grafico_bairros("ocupacao_bairro", "ocupacao_bairro", "taxa_ocupacao_pct")

    _cabecalho("amenities")
    amenities = carregar("amenities")
    if amenities.empty:
        st.info("sem dados")
    else:
        st.dataframe(amenities)
