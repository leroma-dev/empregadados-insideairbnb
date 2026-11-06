"""Funcoes puras que preparam os numeros dos marts para as paginas."""

import pandas as pd


def top_bairros(df: pd.DataFrame, coluna: str, minimo_anuncios: int = 100, n: int = 15) -> pd.DataFrame:
    """Top `n` bairros por `coluna` (decrescente), com pelo menos `minimo_anuncios` anuncios.

    Bairro sem valor em `coluna` e descartado, nunca vira zero.
    """
    if df.empty:
        return df
    base = "anuncios_com_preco" if "anuncios_com_preco" in df.columns else "anuncios"
    filtrado = df[(df[base] >= minimo_anuncios) & df[coluna].notna()]
    return filtrado.sort_values(coluna, ascending=False).head(n).reset_index(drop=True)


def tabela_completa(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Todos os bairros do mart, ordenados por `coluna` (sem o minimo de anuncios)."""
    if df.empty:
        return df
    return df.sort_values(coluna, ascending=False, na_position="last").reset_index(drop=True)


def serie_receita_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Soma `receita_potencial` por `mes`."""
    if df.empty:
        return df
    return df.groupby("mes", as_index=False)["receita_potencial"].sum().sort_values("mes").reset_index(drop=True)


def resumo_multi_host(df: pd.DataFrame) -> dict:
    """Numeros de anfitrioes com varios imoveis; {} se o mart estiver vazio."""
    if df.empty:
        return {}
    linha = df.iloc[0]
    return {
        "fatia_imoveis_pct": float(linha["fatia_imoveis_multi_pct"]),
        "anfitrioes": int(linha["anfitrioes"]),
        "multi_host": int(linha["multi_host"]),
        "fatia_pct": float(linha["fatia_multi_host_pct"]),
    }


def diferenca_pct_inteiro_privado(df: pd.DataFrame) -> float | None:
    """Diferenca percentual do preco mediano do imovel inteiro sobre o quarto privado; None se faltar dado."""
    if df.empty or not {"tipo", "preco_mediano"} <= set(df.columns):
        return None
    por_tipo = df.set_index("tipo")["preco_mediano"]
    if "Entire home/apt" not in por_tipo or "Private room" not in por_tipo or not por_tipo["Private room"]:
        return None
    return float((por_tipo["Entire home/apt"] / por_tipo["Private room"] - 1) * 100)
