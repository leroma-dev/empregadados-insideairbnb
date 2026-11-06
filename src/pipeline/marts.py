"""
Etapa 3: marts. Cria as tabelas de pergunta em mart, a partir de staging,
executando os arquivos SQL de data/mart/ em ordem numérica.

Resumo da spec (docs/spec/08_mart_spec.md):

- M1. Cada tabela de mart é recriada com CREATE OR REPLACE TABLE a partir de
  staging. Motivo: rodar duas vezes dá o mesmo resultado.
- M2. As nove tabelas são gravadas numa única transação. Motivo: se uma
  falhar, nenhuma muda, como no staging.
- M3. Nenhuma consulta de mart escreve em staging ou raw. Motivo: a origem
  da conferência não pode ser alterada pela análise.
- M4. Preço e nota nulos saem só das médias e medianas que dependem deles, e
  a contagem de anúncios mostra quantos ficaram de fora. Motivo: excluir
  nulo sem contar esconderia o tamanho da perda.
- M5. Percentuais com duas casas decimais; preços e receitas em DECIMAL.
  Motivo: DOUBLE não guarda centavos com exatidão.
- M6. Nomes das colunas de saída em português, em snake_case. Motivo: os
  resultados são lidos por quem não programa.
- M7. Os arquivos de data/mart/ rodam em ordem numérica (01 a 09), cada um
  com uma única instrução CREATE OR REPLACE TABLE mart.<nome>. O Python não
  tem SQL de mart. Motivo: o SQL fica revisável e versionado como SQL.
"""

import re
import sys
from pathlib import Path

import duckdb

from pipeline.db import conectar
from pipeline.ingestao import formatar_contagem

PASTA_SQL = Path(__file__).resolve().parents[2] / "data" / "mart"

TABELAS_STAGING = ("anuncios", "calendario", "avaliacoes", "bairros")

PADRAO_ARQUIVO = re.compile(r"^\d{2}_[a-z0-9_]+\.sql$")

PADRAO_CABECALHO = re.compile(r"^--\s*Mart:\s*(mart\.[a-z0-9_]+)\s*$", re.MULTILINE)

PADRAO_CREATE = re.compile(
    r"\A(?:\s*--[^\n]*\n)*\s*CREATE\s+OR\s+REPLACE\s+TABLE\s+(mart\.[a-z0-9_]+)\s+AS\b",
    re.IGNORECASE,
)


class ErroArquivoMart(Exception):
    def __init__(self, arquivo: str, motivo: str):
        self.arquivo = arquivo
        self.motivo = motivo
        super().__init__(f"{arquivo}: {motivo}")


def listar_arquivos(pasta: Path) -> list[Path]:
    """Arquivos de mart de `pasta`, em ordem, com numeração 01, 02, ... sem lacuna.

    Ignora o que não tem o nome de arquivo de mart. Levanta ErroArquivoMart
    antes de qualquer execução se a sequência não começar em 01, tiver lacuna
    ou número repetido.
    """
    arquivos = sorted(p for p in pasta.glob("*.sql") if PADRAO_ARQUIVO.match(p.name))
    for esperado, arquivo in enumerate(arquivos, start=1):
        numero = int(arquivo.name[:2])
        if numero != esperado:
            raise ErroArquivoMart(
                arquivo.name,
                f"esperado número {esperado:02d}, veio {numero:02d}",
            )
    return arquivos


def nome_mart(caminho: Path) -> str:
    """Nome `mart.<nome>` da linha `-- Mart:` do cabeçalho do arquivo."""
    achado = PADRAO_CABECALHO.search(caminho.read_text(encoding="utf-8"))
    if achado is None:
        raise ErroArquivoMart(caminho.name, "sem cabeçalho '-- Mart: mart.<nome>'")
    return achado.group(1)


def verificar_arquivo(con, caminho: Path) -> str:
    """Confere o arquivo sem executar nada e devolve o nome da tabela.

    Exige uma única instrução, no formato CREATE OR REPLACE TABLE <nome> AS,
    com <nome> igual ao do cabeçalho. `con` não é usado; fica por consistência
    com `executar`.
    """
    esperado = nome_mart(caminho)
    instrucoes = duckdb.extract_statements(caminho.read_text(encoding="utf-8"))
    if len(instrucoes) != 1:
        raise ErroArquivoMart(caminho.name, f"esperada 1 instrução, encontradas {len(instrucoes)}")
    achado = PADRAO_CREATE.match(instrucoes[0].query)
    if achado is None:
        raise ErroArquivoMart(caminho.name, "a instrução não é CREATE OR REPLACE TABLE ... AS")
    if achado.group(1) != esperado:
        raise ErroArquivoMart(
            caminho.name, f"cabeçalho diz {esperado}, o CREATE cria {achado.group(1)}"
        )
    return esperado


def executar(con, caminho: Path) -> tuple[str, int]:
    """Executa o arquivo e devolve (nome da tabela, linhas contadas no banco).

    Não abre transação; quem chama decide.
    """
    nome = verificar_arquivo(con, caminho)
    con.execute(caminho.read_text(encoding="utf-8"))
    linhas = con.execute(f"SELECT count(*) FROM {nome}").fetchone()[0]
    return nome, linhas


def executar_todos(con, pasta: Path = PASTA_SQL) -> list[tuple[str, int]]:
    """Cria todas as tabelas de mart numa transação e devolve (tabela, linhas) de cada uma.

    Valida todos os arquivos antes de abrir a transação; erro de execução
    desfaz tudo.
    """
    arquivos = listar_arquivos(pasta)
    for arquivo in arquivos:
        verificar_arquivo(con, arquivo)
    resultado = []
    con.begin()
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS mart")
        for arquivo in arquivos:
            resultado.append(executar(con, arquivo))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return resultado


def faltantes_staging(con) -> list[str]:
    """Nomes `staging.<t>` das tabelas de staging necessárias que não existem."""
    existentes = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
        ).fetchall()
    }
    return [f"staging.{t}" for t in TABELAS_STAGING if t not in existentes]


def main(conectar_fn=conectar, pasta: Path = PASTA_SQL) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    con = conectar_fn()
    try:
        faltantes = faltantes_staging(con)
        if faltantes:
            print(f"Faltam tabelas em staging: {', '.join(faltantes)}")
            print("Rode primeiro: uv run python -m pipeline.staging")
            return 1
        try:
            resultado = executar_todos(con, pasta)
        except (ErroArquivoMart, duckdb.Error) as e:
            print(e)
            return 1
        for tabela, linhas in resultado:
            print(f"{tabela:<26} {formatar_contagem(linhas)} linhas")
        print(f"total {formatar_contagem(sum(n for _, n in resultado))} linhas")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
