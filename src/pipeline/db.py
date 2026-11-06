"""
Acesso ao banco DuckDB do projeto: data/insideairbnb.duckdb.

STATUS: implementação em andamento conforme a spec abaixo.

REGRAS

1. conectar() abre data/insideairbnb.duckdb. O caminho é calculado a partir
   da localização deste arquivo, nunca da pasta corrente.
   Por quê: se o caminho dependesse da pasta de onde o script roda, rodar de
   outra pasta criaria um banco novo lá, e a ingestão ficaria em um arquivo
   que ninguém procura.

2. conectar() cria o arquivo e o schema raw se faltarem.
   Por quê: a ingestão precisa poder rodar do zero, sem passo manual.
   Atenção: o explorador (ui.py) NÃO usa esta função, justamente para não
   abrir um banco vazio que pareça ingestão quebrada.

3. Importar este módulo não abre banco nem cria arquivo.
   Por quê: importar não pode ter efeito colateral. Testes e ferramentas
   importam o módulo sem intenção de gravar nada.

4. gravar(nome_qualificado, df) faz CREATE OR REPLACE TABLE e devolve a
   contagem de linhas consultada no banco, não len(df).
   Por quê: a contagem mostrada ao usuário precisa ser a do que de fato ficou
   gravado. CREATE OR REPLACE faz rodar duas vezes dar o mesmo resultado, sem
   acumular linhas.

CRITÉRIOS DE ACEITE

- Importar pipeline.db não abre banco nem cria arquivo.
- conectar() chamado de outra pasta cria data/insideairbnb.duckdb dentro do
  projeto, não na pasta corrente.
- gravar() com DataFrame de 3 linhas devolve 3; rodar de novo continua devolvendo 3.
"""

from pathlib import Path

import duckdb
import pandas as pd


def caminho_banco() -> Path:
    """Caminho fixo do banco: data/ na raiz do projeto, qualquer que seja a pasta corrente."""
    return Path(__file__).resolve().parents[2] / "data" / "insideairbnb.duckdb"


def conectar() -> duckdb.DuckDBPyConnection:
    """Abre o banco, criando pasta, arquivo e schema raw se faltarem."""
    caminho = caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho))
    # Padrão do DuckDB é ~80% da RAM (6,2 GiB aqui). Com 2 GB ele grava em disco em vez de crescer
    # até o kernel matar o VS Code por falta de memória.
    con.execute("SET memory_limit = '2GB'").fetchall()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    return con


def gravar(con: duckdb.DuckDBPyConnection, nome_qualificado: str, df: pd.DataFrame) -> int:
    """Recria a tabela a partir do DataFrame e devolve a contagem consultada no banco.

    nome_qualificado vem só de constantes internas (ex.: raw.anuncios), nunca de entrada externa.
    """
    con.register("_df", df)
    # fetchall em todo execute: sem isso o resultado fica aberto e a próxima
    # chamada na conexão falha.
    con.execute(f"CREATE OR REPLACE TABLE {nome_qualificado} AS SELECT * FROM _df").fetchall()
    con.unregister("_df")
    return con.execute(f"SELECT count(*) FROM {nome_qualificado}").fetchall()[0][0]


def anexar(con: duckdb.DuckDBPyConnection, nome_qualificado: str, df: pd.DataFrame) -> None:
    """Acrescenta um bloco à tabela, que já foi criada por gravar() na mesma transação."""
    con.register("_df", df)
    con.execute(f"INSERT INTO {nome_qualificado} SELECT * FROM _df").fetchall()
    con.unregister("_df")
