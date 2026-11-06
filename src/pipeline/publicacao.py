"""
Publicação: exporta os marts para Parquet em data/publicacao/, mais atualizacao.json.

Grava numa pasta temporária ao lado do destino e só move para o lugar se todas
as exportações derem certo, para não deixar arquivo pela metade.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dashboard.dados import MARTS, PASTA_PUBLICACAO
from pipeline.db import conectar
from pipeline.ingestao import formatar_contagem


def faltantes_mart(con, nomes: tuple[str, ...] = MARTS) -> list[str]:
    """Nomes `mart.<n>` que não existem no banco."""
    existentes = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'mart'"
        ).fetchall()
    }
    return [f"mart.{n}" for n in nomes if n not in existentes]


def exportar(con, pasta: Path, nomes: tuple[str, ...]) -> list[tuple[str, int]]:
    """Grava um Parquet por mart e atualizacao.json; devolve (nome, linhas) de cada um."""
    pasta = Path(pasta)
    pasta.parent.mkdir(parents=True, exist_ok=True)
    temporaria = Path(tempfile.mkdtemp(prefix=f".{pasta.name}-", dir=pasta.parent))
    try:
        resultado = []
        for nome in nomes:
            destino = str(temporaria / f"{nome}.parquet").replace("'", "''")
            con.execute(f"COPY (SELECT * FROM mart.{nome}) TO '{destino}' (FORMAT parquet)")
            linhas = con.execute(f"SELECT count(*) FROM mart.{nome}").fetchone()[0]
            resultado.append((nome, linhas))
        (temporaria / "atualizacao.json").write_text(
            json.dumps(
                {
                    "gerado_em": datetime.now(timezone.utc).isoformat(),
                    "marts": dict(resultado),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        pasta.mkdir(exist_ok=True)
        for arquivo in temporaria.iterdir():
            os.replace(arquivo, pasta / arquivo.name)
    finally:
        shutil.rmtree(temporaria, ignore_errors=True)
    return resultado


def main(conectar_fn=conectar, pasta: Path = PASTA_PUBLICACAO) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    con = conectar_fn()
    try:
        faltantes = faltantes_mart(con)
        if faltantes:
            print(f"Faltam tabelas em mart: {', '.join(faltantes)}")
            print("Rode primeiro: uv run python -m pipeline.marts")
            return 1
        resultado = exportar(con, pasta, MARTS)
        for nome, linhas in resultado:
            print(f"{nome:<26} {formatar_contagem(linhas)} linhas")
        print(f"total {formatar_contagem(sum(n for _, n in resultado))} linhas")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
