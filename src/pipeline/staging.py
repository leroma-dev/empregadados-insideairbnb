"""
Etapa 2: staging. Converte raw (tudo VARCHAR) em tipos decididos, numa
tabela por tabela de raw, no schema staging.

Resumo da spec (docs/spec/06_staging_spec.md):

- R1. Nenhuma linha some em silêncio; saída só por duplicata exata, contada.
  Motivo: contagem que some sem registro impede conferir o resultado.
- R2. Nenhum nulo é apagado nem preenchido; conversão que falha para tudo.
  Motivo: nulo fabricado pela conversão é indistinguível de nulo verdadeiro.
- R3. CREATE OR REPLACE a partir de raw. Motivo: reexecutar não acumula linhas.
- R4. As quatro tabelas numa transação. Motivo: nunca deixar staging meio novo.
- R5. Nenhum valor trocado por "plausível". Motivo: valor inventado parece real.
- R6. Vazio vira NULL em colunas que não são texto. Motivo: vazio em coluna
  numérica ou de data não é valor; quebraria conversões e somas.

Tipos: price em DECIMAL(10,2) porque DOUBLE não guarda centavos com exatidão;
t/f em BOOLEAN porque é código, não texto livre; datas sem hora em DATE porque
a origem traz só o dia.

REGRAS mapeia cada coluna para a regra de conversão: "texto" passa sem
conversão; as demais são as conversões tipadas da spec.
"""

import re
import sys

import duckdb

from pipeline.db import conectar
from pipeline.ingestao import formatar_contagem

TABELAS = ("anuncios", "calendario", "avaliacoes", "bairros")

REGRAS: dict[str, list[tuple[str, str]]] = {
    "anuncios": [
        ("id", "bigint"),
        ("listing_url", "texto"),
        ("scrape_id", "bigint"),
        ("last_scraped", "texto"),
        ("source", "texto"),
        ("name", "texto"),
        ("description", "texto"),
        ("neighborhood_overview", "texto"),
        ("picture_url", "texto"),
        ("host_id", "bigint"),
        ("host_url", "texto"),
        ("host_profile_id", "texto"),
        ("host_profile_url", "texto"),
        ("host_name", "texto"),
        ("host_since", "data"),
        ("hosts_time_as_user_years", "texto"),
        ("hosts_time_as_user_months", "texto"),
        ("hosts_time_as_host_years", "texto"),
        ("hosts_time_as_host_months", "texto"),
        ("host_location", "texto"),
        ("host_about", "texto"),
        ("host_response_time", "texto"),
        ("host_response_rate", "texto"),
        ("host_acceptance_rate", "texto"),
        ("host_is_superhost", "boolean"),
        ("host_thumbnail_url", "texto"),
        ("host_picture_url", "texto"),
        ("host_neighbourhood", "texto"),
        ("host_listings_count", "texto"),
        ("host_total_listings_count", "texto"),
        ("host_verifications", "texto"),
        ("host_has_profile_pic", "texto"),
        ("host_identity_verified", "boolean"),
        ("neighbourhood", "texto"),
        ("neighbourhood_cleansed", "texto"),
        ("neighbourhood_group_cleansed", "texto"),
        ("latitude", "double"),
        ("longitude", "double"),
        ("property_type", "texto"),
        ("room_type", "texto"),
        ("accommodates", "integer"),
        ("bathrooms", "texto"),
        ("bathrooms_text", "texto"),
        ("bedrooms", "texto"),
        ("beds", "texto"),
        ("amenities", "texto"),
        ("price", "decimal_preco"),
        ("price_quote_checkin_date", "texto"),
        ("price_quote_checkout_date", "texto"),
        ("price_quote_total_price", "texto"),
        ("price_quote_price_per_night", "texto"),
        ("price_quote_raw", "texto"),
        ("minimum_nights", "integer"),
        ("maximum_nights", "integer"),
        ("minimum_minimum_nights", "texto"),
        ("maximum_minimum_nights", "texto"),
        ("minimum_maximum_nights", "texto"),
        ("maximum_maximum_nights", "texto"),
        ("minimum_nights_avg_ntm", "texto"),
        ("maximum_nights_avg_ntm", "texto"),
        ("calendar_updated", "texto"),
        ("has_availability", "texto"),
        ("availability_30", "texto"),
        ("availability_60", "texto"),
        ("availability_90", "texto"),
        ("availability_365", "integer"),
        ("calendar_last_scraped", "texto"),
        ("number_of_reviews", "integer"),
        ("number_of_reviews_ltm", "texto"),
        ("number_of_reviews_l30d", "texto"),
        ("availability_eoy", "texto"),
        ("number_of_reviews_ly", "texto"),
        ("estimated_occupancy_l365d", "texto"),
        ("estimated_revenue_l365d", "texto"),
        ("first_review", "data"),
        ("last_review", "data"),
        ("review_scores_rating", "double"),
        ("review_scores_accuracy", "double"),
        ("review_scores_cleanliness", "double"),
        ("review_scores_checkin", "double"),
        ("review_scores_communication", "double"),
        ("review_scores_location", "double"),
        ("review_scores_value", "double"),
        ("license", "texto"),
        ("instant_bookable", "boolean"),
        ("calculated_host_listings_count", "texto"),
        ("calculated_host_listings_count_entire_homes", "texto"),
        ("calculated_host_listings_count_private_rooms", "texto"),
        ("calculated_host_listings_count_shared_rooms", "texto"),
        ("reviews_per_month", "texto"),
    ],
    "calendario": [
        ("listing_id", "bigint"),
        ("date", "data"),
        ("available", "boolean"),
        ("minimum_nights", "integer"),
        ("maximum_nights", "integer"),
    ],
    "avaliacoes": [
        ("listing_id", "bigint"),
        ("id", "bigint"),
        ("date", "data"),
        ("reviewer_id", "bigint"),
        ("reviewer_name", "texto"),
        ("comments", "texto"),
    ],
    "bairros": [
        ("neighbourhood", "texto"),
        ("neighbourhood_group", "texto"),
    ],
}

CHAVES: dict[str, tuple[str, ...]] = {
    "anuncios": ("id",),
    "calendario": ("listing_id", "date"),
    "avaliacoes": ("id", "listing_id"),
    "bairros": ("neighbourhood",),
}

# Expressão regular completa por regra. "texto" não tem padrão: passa sem conversão.
PADROES: dict[str, str] = {
    "bigint": r"-?[0-9]+",
    "integer": r"-?[0-9]+",
    "double": r"-?[0-9]+(\.[0-9]+)?",
    "boolean": r"[tf]",
    "data": r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
    "decimal_preco": r"\$([0-9]{1,3}(,[0-9]{3})*|[0-9]{1,8})\.[0-9]{2}",
}


def primeiro_invalido(con, nome_raw: str, coluna: str, regra: str) -> str | None:
    """Primeiro valor não NULL que não casa com o padrão da regra, ou None.

    Valida por regexp_full_match, nunca por TRY_CAST: TRY_CAST devolveria NULL
    para o que falha e esconderia o valor ruim (R2).
    nome_raw e coluna vêm só de constantes internas, nunca de entrada externa.
    """
    padrao = PADROES[regra].replace("'", "''")
    linha = con.execute(
        f"SELECT {coluna} FROM {nome_raw} "
        f"WHERE {coluna} IS NOT NULL AND NOT regexp_full_match({coluna}, '{padrao}') LIMIT 1"
    ).fetchall()
    return linha[0][0] if linha else None


class ErroConversao(Exception):
    def __init__(self, tabela: str, coluna: str, exemplo: str):
        self.tabela = tabela
        self.coluna = coluna
        self.exemplo = exemplo
        super().__init__(f"{tabela}.{coluna}: valor inválido {exemplo!r}")


def expressao_sql(coluna: str, regra: str) -> str:
    """Expressão de SELECT que converte a coluna; o nome de saída é o da coluna."""
    expressoes = {
        "texto": coluna,
        "bigint": f"CAST({coluna} AS BIGINT)",
        "integer": f"CAST({coluna} AS INTEGER)",
        "double": f"CAST({coluna} AS DOUBLE)",
        "decimal_preco": f"CAST(replace(replace({coluna}, '$', ''), ',', '') AS DECIMAL(10,2))",
        "boolean": f"CASE {coluna} WHEN 't' THEN true WHEN 'f' THEN false END",
        "data": f"CAST({coluna} AS DATE)",
    }
    return expressoes[regra]


def converter(con, tabela: str) -> None:
    """Valida colunas não texto de raw.<tabela>; levanta ErroConversao no primeiro valor ruim."""
    for coluna, regra in REGRAS[tabela]:
        if regra == "texto":
            continue
        exemplo = primeiro_invalido(con, f"raw.{tabela}", coluna, regra)
        if exemplo is not None:
            raise ErroConversao(tabela, coluna, exemplo)
        # count(c), não count(*): o DuckDB poda a projeção e não executaria o CAST.
        # Valor que casa com o padrão mas o CAST recusa (data 2024-02-30, overflow): sem TRY_CAST.
        try:
            con.execute(
                f"SELECT count(c) FROM "
                f"(SELECT {expressao_sql(coluna, regra)} AS c FROM raw.{tabela})"
            ).fetchall()
        except duckdb.Error as erro:
            achado = re.search(r"\"([^\"]*)\"|'([^']*)'", str(erro))
            raise ErroConversao(
                tabela, coluna, (achado.group(1) or achado.group(2)) if achado else str(erro)
            ) from erro


class ErroChaveConflitante(Exception):
    def __init__(self, tabela: str, chave: tuple, linhas: list[tuple]):
        self.tabela = tabela
        self.chave = chave
        self.linhas = linhas
        super().__init__(
            f"{tabela}: chave {chave!r} com {len(linhas)} linhas de conteúdo diferente"
        )


def linhas_repetidas(con, tabela_raw: str) -> int:
    """Linhas que saem por serem cópia exata de outra. DISTINCT trata NULL como igual a NULL."""
    total = con.execute(f"SELECT count(*) FROM {tabela_raw}").fetchone()[0]
    unicas = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT * FROM {tabela_raw})").fetchone()[
        0
    ]
    return total - unicas


def remover_repetidas(con, tabela_raw: str, chave: tuple[str, ...]) -> int:
    """Verifica que, sem as cópias exatas, nenhuma chave repete; devolve quantas linhas saem.

    Não grava nada: a escrita é da gravação do staging. Chave com NULL fica de
    fora da verificação: nulo não vira conflito nem apaga linha.
    """
    colunas = ", ".join(chave)
    nao_nulas = " AND ".join(f"{c} IS NOT NULL" for c in chave)
    unicas = f"(SELECT DISTINCT * FROM {tabela_raw})"
    repetida = con.execute(
        f"SELECT {colunas} FROM {unicas} WHERE {nao_nulas} "
        f"GROUP BY {colunas} HAVING count(*) > 1 LIMIT 1"
    ).fetchall()
    if repetida:
        valores = tuple(repetida[0])
        filtro = " AND ".join(f"{c} = ?" for c in chave)
        linhas = con.execute(f"SELECT * FROM {unicas} WHERE {filtro}", list(valores)).fetchall()
        raise ErroChaveConflitante(tabela_raw, valores, linhas)
    return linhas_repetidas(con, tabela_raw)


def faltantes_raw(con) -> list[str]:
    """Nomes de TABELAS cuja tabela raw.<nome> não existe."""
    existentes = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
        ).fetchall()
    }
    return [t for t in TABELAS if t not in existentes]


def transformar(con) -> list[tuple[str, int, int]]:
    """Cria staging.<t> a partir de raw.<t> para as quatro tabelas, numa transação.

    Primeiro valida tudo (converter e remover_repetidas, sem escrita); só então cria.
    Devolve (tabela, linhas_em_staging, linhas_removidas) na ordem de TABELAS.
    """
    removidas = {}
    for tabela in TABELAS:
        converter(con, tabela)
        removidas[tabela] = remover_repetidas(con, f"raw.{tabela}", CHAVES[tabela])
    resultado = []
    con.begin()
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS staging")
        for tabela in TABELAS:
            colunas = ", ".join(f"{expressao_sql(c, r)} AS {c}" for c, r in REGRAS[tabela])
            con.execute(
                f"CREATE OR REPLACE TABLE staging.{tabela} AS "
                f"SELECT {colunas} FROM (SELECT DISTINCT * FROM raw.{tabela})"
            )
            linhas = con.execute(f"SELECT count(*) FROM staging.{tabela}").fetchone()[0]
            resultado.append((tabela, linhas, removidas[tabela]))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return resultado


def nulos_mantidos(con, tabela: str) -> list[tuple[str, int]]:
    """Colunas de staging.<tabela> com nulo acima de zero, com a contagem, numa consulta."""
    colunas = [c for c, _ in REGRAS[tabela]]
    contagens = ", ".join(f"count(*) FILTER (WHERE {c} IS NULL)" for c in colunas)
    linha = con.execute(f"SELECT {contagens} FROM staging.{tabela}").fetchone()
    return [(c, n) for c, n in zip(colunas, linha) if n > 0]


def main(conectar_fn=conectar) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    con = conectar_fn()
    try:
        faltantes = faltantes_raw(con)
        if faltantes:
            print(f"Faltam tabelas em raw: {', '.join(faltantes)}")
            print("Rode primeiro: uv run python -m pipeline.ingestao")
            return 1
        try:
            resultado = transformar(con)
        except ErroConversao as e:
            print(f"Erro de conversão em {e.tabela}, coluna {e.coluna}: valor {e.exemplo!r}")
            return 1
        except ErroChaveConflitante as e:
            print(f"Chave conflitante em {e.tabela}: chave {e.chave!r}, linhas:")
            for linha in e.linhas:
                print(f"    {linha!r}")
            return 1
        total = 0
        for tabela, linhas, removidas in resultado:
            total += linhas
            print(
                f"staging.{tabela:<12} {formatar_contagem(linhas)} linhas "
                f"({formatar_contagem(removidas)} duplicatas)"
            )
            nulos = nulos_mantidos(con, tabela)
            if nulos:
                print(
                    "    nulos mantidos: "
                    + ", ".join(f"{c} {formatar_contagem(n)}" for c, n in nulos)
                )
        print(f"total {formatar_contagem(total)} linhas")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
