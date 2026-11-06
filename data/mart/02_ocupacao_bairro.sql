-- Mart: mart.ocupacao_bairro
-- Pergunta 2: taxa de ocupação estimada por bairro.
-- Contexto: Fonte: staging.calendario (available) e staging.anuncios. Ocupado = available = false; taxa = dias ocupados / dias do calendário.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.ocupacao_bairro AS
WITH cal AS (
    SELECT listing_id,
           count(*) FILTER (WHERE NOT available) AS dias_indisponiveis,
           count(*) AS dias
    FROM staging.calendario
    GROUP BY 1
)
SELECT a.neighbourhood_cleansed AS bairro,
       count(*) AS anuncios,
       round(100.0 * sum(c.dias_indisponiveis) / sum(c.dias), 2) AS taxa_ocupacao_pct
FROM staging.anuncios a
JOIN cal c ON c.listing_id = a.id
GROUP BY 1
ORDER BY 1;
