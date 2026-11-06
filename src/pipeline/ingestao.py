"""
Ingestão raw: os quatro arquivos de data/raw/ entram no DuckDB, schema raw,
exatamente como chegaram.

STATUS: implementação em andamento conforme a spec abaixo.

MAPA ARQUIVO -> TABELA

    listings.csv.gz      -> raw.anuncios
    calendar.csv.gz      -> raw.calendario
    reviews.csv.gz       -> raw.avaliacoes
    neighbourhoods.csv   -> raw.bairros

Os nomes em português são o vocabulário que o desenvolvedor digita de memória
em JOINs.

REGRAS

1. Antes de abrir o banco, verifica se os quatro arquivos existem em data/raw/.
   Faltando qualquer um: lista os que faltam, mostra a pasta onde procurou e
   encerra com sys.exit(1). Não ingere nada parcialmente.
   Por quê: ingerir três tabelas em silêncio gera um dashboard errado que
   parece certo.

2. Proibições (a regra central desta etapa):
   nenhuma conversão de tipo, nenhuma linha descartada ou deduplicada, nenhum
   nome de coluna alterado, nenhum valor corrigido, preenchido ou normalizado.
   Data continua texto; nulo continua nulo.
   Por quê: a fronteira entre "o dado que chegou" e "o dado que eu decidi"
   precisa existir em um lugar só. Esse lugar é a passagem de raw para staging
   (etapa 2). Se a correção acontecer aqui, a fronteira some.

3. Reexecução: a tabela é recriada com CREATE OR REPLACE, nunca acrescentada.
   Rodar dez vezes dá o mesmo resultado que rodar uma.
   Por quê: permite errar e rodar de novo sem medo.

4. Leitura: encoding="utf-8" declarado, nunca adivinhado. Os .csv.gz são lidos
   direto, sem descompactar. Campo vazio vira nulo, não string vazia.
   Por quê: a leitura não pode depender de detecção automática, que erra sem
   aviso.

5. Tipagem: toda coluna entra como texto (dtype=str), com inferência
   desligada.
   Por quê: a inferência lê CEP com zero à esquerda como número, e o zero
   desaparece sem aviso. A conversão acontece na etapa 2, como decisão
   registrada.

6. Valores que o pandas trata como nulo por padrão ("NA", "null", "N/A",
   "NaN") devem continuar texto. Usar keep_default_na=False e na_values=[""].
   Por quê: sem isso, o pandas converte esses textos em nulo sem aviso, o que
   é uma correção de valor escondida dentro da ingestão.

7. Escrita atômica: toda a ingestão roda em uma única transação. Se falhar
   no meio, o banco fica no estado anterior, não parcial.
   Por quê: um banco com algumas tabelas novas e outras antigas seria um
   estado que ninguém decidiu ter.

8. Saída na tela: uma linha por tabela, com nome qualificado e contagem de
   linhas vinda do banco (não do DataFrame), milhar separado por ponto. Uma
   linha final com o total. stdout reconfigurado para utf-8.
   Por quê: a saída é o único instrumento de conferência nesta etapa. O
   usuário roda no Prompt de Comando do Windows, onde acento sai embaralhado
   sem essa configuração.

9. O script termina sozinho e devolve o terminal. Nenhum processo fica de pé.

CRITÉRIOS DE ACEITE

- A execução imprime uma linha por tabela (quatro) e o total de registros.
- Duas execuções seguidas imprimem exatamente a mesma coisa.
- SELECT * FROM raw.anuncios devolve todas as colunas como VARCHAR.
- Remover um dos quatro arquivos faz o script parar antes de gravar qualquer tabela.
- O processo termina sozinho.

SEPARAÇÃO

Este módulo não sobe servidor, não abre navegador e não depende da extensão
ui do DuckDB. Não importa src/ui/ui.py, e src/ui/ui.py não importa este módulo.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.db import anexar, conectar, gravar

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Linhas por bloco de leitura. Ler reviews.csv.gz inteiro como texto estourou a memória
# (8 GB, OOM). Cada bloco é lido com as mesmas opções de ler_arquivo; o resultado é igual.
TAMANHO_BLOCO = 100_000

MAPA: dict[str, str] = {
    "listings.csv.gz": "raw.anuncios",
    "calendar.csv.gz": "raw.calendario",
    "reviews.csv.gz": "raw.avaliacoes",
    "neighbourhoods.csv": "raw.bairros",
}


def ler_arquivo(caminho: Path) -> pd.DataFrame:
    """Lê um arquivo bruto como texto, sem conversão e sem trocar textos por nulo."""
    return pd.read_csv(
        caminho,
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )


def ler_em_blocos(caminho: Path, linhas: int) -> Iterator[pd.DataFrame]:
    """Mesmas opções de ler_arquivo, em blocos de no máximo `linhas` linhas."""
    return pd.read_csv(
        caminho,
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        chunksize=linhas,
    )


def colunas_vazias(caminho: Path) -> pd.DataFrame:
    """Só o cabeçalho, para criar a tabela quando o arquivo não tem linhas de dados."""
    return pd.read_csv(caminho, encoding="utf-8", dtype=str, nrows=0)


def arquivos_faltantes(pasta: Path) -> list[str]:
    """Nomes de MAPA que não existem em pasta, na ordem de MAPA."""
    return [nome for nome in MAPA if not (pasta / nome).exists()]


def formatar_contagem(n: int) -> str:
    """Milhar separado por ponto: 1550922 -> '1.550.922'."""
    return f"{n:,}".replace(",", ".")


def ingerir(con, pasta: Path) -> list[tuple[str, int]]:
    """Grava as tabelas de MAPA numa única transação; qualquer falha desfaz tudo."""
    con.begin()
    try:
        resultado = []
        for nome, tabela in MAPA.items():
            caminho = pasta / nome
            blocos = ler_em_blocos(caminho, TAMANHO_BLOCO)
            primeiro = next(blocos, None)
            if primeiro is None:
                gravar(con, tabela, colunas_vazias(caminho))
            else:
                gravar(con, tabela, primeiro)
                for bloco in blocos:
                    anexar(con, tabela, bloco)
            resultado.append(
                (tabela, con.execute(f"SELECT count(*) FROM {tabela}").fetchall()[0][0])
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return resultado


def main(pasta: Path = RAW_DIR, conectar_fn=conectar) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    faltantes = arquivos_faltantes(pasta)
    if faltantes:
        print(f"Faltam arquivos em {pasta}:")
        for nome in faltantes:
            print(f"  - {nome}")
        return 1
    try:
        con = conectar_fn()
    except duckdb.Error as erro:
        print(f"Não foi possível abrir o banco: {erro}")
        print("Se o explorador (ui) estiver aberto, feche-o e rode a ingestão de novo.")
        return 1
    try:
        linhas = ingerir(con, pasta)
    finally:
        con.close()
    for tabela, n in linhas:
        print(f"{tabela:<22} {formatar_contagem(n)}")
    total = sum(n for _, n in linhas)
    print(f"{'total':<22} {formatar_contagem(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
