"""Pagina do investidor: so desenha; os numeros vem de preparo."""

import streamlit as st

from dashboard.dados_ui import carregar_cache as carregar
from dashboard.graficos import cabecalho as _cabecalho, grafico_bairros
from dashboard.preparo import resumo_multi_host, serie_receita_mensal


def desenhar() -> None:
    _cabecalho("receita_mensal")
    receita = serie_receita_mensal(carregar("receita_mensal_anuncio"))
    if receita.empty:
        st.info("sem dados")
    else:
        st.line_chart(receita, x="mes", y="receita_potencial")

    grafico_bairros("ocupacao_bairro", "ocupacao_bairro", "taxa_ocupacao_pct")

    _cabecalho("sazonalidade")
    sazonal = carregar("sazonalidade_reviews")
    if sazonal.empty:
        st.info("sem dados")
    else:
        st.bar_chart(sazonal, x="mes_do_ano", y="media_reviews_por_ano")

    _cabecalho("reviews_mensal")
    reviews = carregar("reviews_mensal")
    if reviews.empty:
        st.info("sem dados")
    else:
        st.line_chart(reviews, x="mes", y="reviews")

    _cabecalho("multi_host")
    resumo = resumo_multi_host(carregar("multi_host"))
    if not resumo:
        st.info("sem dados")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Anfitriões", resumo["anfitrioes"])
        c2.metric("Com vários imóveis", resumo["multi_host"])
        c3.metric("Fatia dos anfitriões (%)", resumo["fatia_pct"])
        c4.metric("Fatia dos anúncios (%)", resumo["fatia_imoveis_pct"])

    _cabecalho("superhost")
    superhost = carregar("superhost")
    if superhost.empty:
        st.info("sem dados")
    else:
        st.dataframe(superhost)
