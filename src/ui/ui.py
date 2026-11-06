"""
Explorador do banco pelo navegador: abre data/insideairbnb.duckdb na
interface web da extensão ui do DuckDB.

STATUS: implementação em andamento conforme a spec abaixo.

Uso previsto: uv run python src/ui/ui.py

REGRAS

U1. O que faz: abre data/insideairbnb.duckdb, executa INSTALL ui; LOAD ui;
    e CALL start_ui(), que sobe o servidor em http://localhost:4213 e abre
    o navegador.

U2. Fica de pé até Ctrl+C: a extensão serve enquanto a conexão estiver viva.
    O script mantém o processo rodando, imprime a URL e a instrução
    "Ctrl+C para encerrar". No Ctrl+C fecha a conexão e sai sem traceback.
    Por quê: o arquivo .duckdb aceita um único processo escrevendo. Com este
    script de pé, a ingestão falha com "Could not set lock on file". Saber
    exatamente como desligar o servidor faz parte da ferramenta.

U3. Não cria banco: se data/insideairbnb.duckdb não existir, diz que é
    preciso rodar a ingestão antes e encerra com sys.exit(1).
    NÃO usa conectar() de pipeline/db.py, que cria o arquivo quando ele falta.
    Por quê: um banco vazio aberto no navegador parece ingestão quebrada.

U4. Separação: este script não importa pipeline/ingestao.py, e a ingestão
    não importa este script. A ingestão não sobe servidor, não abre navegador
    e não depende da extensão ui para rodar.
    Por quê: cada etapa roda sem a outra.

U5. Saída na tela: stdout reconfigurado para utf-8, pelo mesmo motivo da
    ingestão (Prompt de Comando do Windows).

CRITÉRIOS DE ACEITE

- uv run python src/ui/ui.py abre o navegador em localhost:4213, com o schema
  raw e as quatro tabelas (anuncios, calendario, avaliacoes, bairros).
- Ctrl+C devolve o terminal sem traceback, e logo depois a ingestão roda sem
  erro de lock.
- Renomear data/insideairbnb.duckdb faz o script parar com a mensagem, sem
  criar arquivo novo.
"""

import sys
import time
from collections.abc import Callable
from pathlib import Path

import duckdb

BANCO = Path(__file__).resolve().parents[2] / "data" / "insideairbnb.duckdb"
PORTA = 4213


def verificar_banco(caminho: Path) -> None:
    """Sai com código 1 se o banco não existir. Não cria arquivo."""
    if not caminho.exists():
        print(f"Banco não encontrado: {caminho}")
        print("Rode a ingestão antes: scripts/comandos_uv.sh ingestao")
        sys.exit(1)


def _esperar_para_sempre() -> None:
    # Laço com sleep: Event().wait() sem tempo limite pode não responder ao Ctrl+C no Windows.
    while True:
        time.sleep(1)


def main(caminho: Path = BANCO, esperar: Callable[[], None] | None = None) -> int:
    """Sobe o explorador até Ctrl+C. Devolve 0 no Ctrl+C e 1 em erro do DuckDB."""
    sys.stdout.reconfigure(encoding="utf-8")
    verificar_banco(caminho)
    try:
        con = duckdb.connect(str(caminho))
    except duckdb.Error as erro:
        print(f"Não foi possível abrir o banco: {erro}")
        return 1
    try:
        con.execute("INSTALL ui; LOAD ui;")
        # start_ui() sobe o servidor em localhost:4213 (porta padrão) e abre o navegador.
        con.execute("CALL start_ui()")
        print(f"Explorador em http://localhost:{PORTA}")
        print("Ctrl+C para encerrar")
        (esperar or _esperar_para_sempre)()
    except KeyboardInterrupt:
        pass
    except duckdb.Error as erro:
        print(f"Falha ao subir o explorador: {erro}")
        return 1
    finally:
        con.close()  # isso também encerra o servidor
    return 0


if __name__ == "__main__":
    sys.exit(main())
