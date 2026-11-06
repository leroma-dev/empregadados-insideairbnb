"""Leitura dos marts para as paginas, com cache do Streamlit (so na camada de UI)."""

import pandas as pd
import streamlit as st

from dashboard import dados


@st.cache_data(show_spinner=False)
def carregar_cache(nome: str) -> pd.DataFrame:
    """`dados.carregar` com cache; a origem e decidida dentro de `dados`."""
    return dados.carregar(nome)
