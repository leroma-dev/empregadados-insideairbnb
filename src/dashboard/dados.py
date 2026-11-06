"""
Camada de leitura do dashboard: lê os marts do banco (somente leitura) ou dos Parquet publicados.
"""

import os
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.db import caminho_banco as _caminho_banco_padrao


def caminho_banco() -> Path:
    """Caminho do arquivo .duckdb do projeto."""
    return Path(_caminho_banco_padrao())


MARTS: tuple[str, ...] = (
    "preco_bairro",
    "ocupacao_bairro",
    "receita_mensal_anuncio",
    "multi_host",
    "reviews_mensal",
    "inteiro_vs_privado",
    "superhost",
    "amenities",
    "sazonalidade_reviews",
)

PASTA_PUBLICACAO: Path = Path(__file__).resolve().parents[2] / "data" / "publicacao"


class ErroOrigem(Exception):
    """Falha ao ler a origem dos dados (banco em uso, arquivo ausente)."""


def origem() -> str:
    """Origem dos dados: DASHBOARD_ORIGEM, senão 'banco' se o .duckdb existe, senão 'publicacao'."""
    forcada = os.environ.get("DASHBOARD_ORIGEM")
    if forcada:
        if forcada not in ("banco", "publicacao"):
            raise ValueError(f"DASHBOARD_ORIGEM inválida: {forcada!r} (use 'banco' ou 'publicacao')")
        return forcada
    if caminho_banco().exists():
        return "banco"
    return "publicacao"


def caminho_banco_padrao() -> Path:
    """Resolve o caminho do banco pela função do módulo (permite substituir nos testes)."""
    return caminho_banco()


def _conectar_leitura(caminho: Path) -> duckdb.DuckDBPyConnection:
    """Única função que abre o banco, sempre em modo somente leitura."""
    return duckdb.connect(str(caminho), read_only=True)


def carregar(
    nome: str,
    origem_escolhida: str | None = None,
    caminho_banco: Path | None = None,
    pasta: Path = PASTA_PUBLICACAO,
) -> pd.DataFrame:
    """Devolve o mart `nome` como DataFrame, do banco ou do Parquet publicado."""
    if nome not in MARTS:
        raise ValueError(f"Mart desconhecido: {nome!r}")
    escolhida = origem_escolhida or origem()

    if escolhida == "publicacao":
        arquivo = Path(pasta) / f"{nome}.parquet"
        if not arquivo.exists():
            raise ErroOrigem(f"arquivo {arquivo.name} ausente em data/publicacao")
        con = duckdb.connect()
        try:
            return con.execute("SELECT * FROM read_parquet(?)", [str(arquivo)]).df()
        except duckdb.Error as erro:
            raise ErroOrigem(f"Não foi possível ler {arquivo.name}.") from erro
        finally:
            con.close()

    caminho = Path(caminho_banco) if caminho_banco else caminho_banco_padrao()
    try:
        con = _conectar_leitura(caminho)
    except duckdb.Error as erro:
        raise ErroOrigem(
            "Não foi possível abrir o banco em leitura: feche o explorador (ui) e tente de novo."
        ) from erro
    try:
        # nome já validado contra MARTS acima
        return con.execute(f"SELECT * FROM mart.{nome}").df()
    except duckdb.Error as erro:
        raise ErroOrigem(f"Não foi possível ler mart.{nome}.") from erro
    finally:
        con.close()
