"""Ponto de entrada do dashboard: navegação entre as duas páginas e rodapé."""

import json
import sys

import streamlit as st

from dashboard.dados import PASTA_PUBLICACAO, ErroOrigem, origem
from dashboard.paginas import anfitriao, investidor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ROTULO_ORIGEM = {"banco": "banco local", "publicacao": "publicação"}
MSG_ORIGEM_INVALIDA = "DASHBOARD_ORIGEM tem valor inválido; use 'banco' ou 'publicacao'."


def erro_origem() -> str | None:
    """Mensagem de erro se DASHBOARD_ORIGEM tiver valor inválido; None caso contrário."""
    try:
        origem()
    except ValueError:
        return MSG_ORIGEM_INVALIDA
    return None


def texto_rodape() -> str:
    """Texto do rodapé: data de geração (de atualizacao.json) e origem dos dados."""
    try:
        conteudo = json.loads((PASTA_PUBLICACAO / "atualizacao.json").read_text(encoding="utf-8"))
        data = str(conteudo["gerado_em"])[:10]
        if not data:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        data = "data desconhecida"
    else:
        data = f"dados gerados em {data}"
    try:
        fonte = origem()
    except ValueError:
        return f"{data} · origem: indisponível"
    return f"{data} · origem: {_ROTULO_ORIGEM.get(fonte, fonte)}"


def main() -> None:
    st.set_page_config(page_title="Airbnb Rio de Janeiro", layout="wide")
    pagina = st.navigation(
        [
            st.Page(anfitriao.desenhar, title="Anfitrião", url_path="anfitriao", default=True),
            st.Page(investidor.desenhar, title="Investidor", url_path="investidor"),
        ]
    )
    try:
        pagina.run()
    except ErroOrigem as erro:
        st.error(str(erro))
    if mensagem := erro_origem():
        st.error(mensagem)
    st.divider()
    st.caption(texto_rodape())


if __name__ == "__main__":
    main()
