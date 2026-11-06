-- Mart: mart.superhost
-- Pergunta 7: superhosts têm notas e ocupação maiores?
-- Contexto: Fonte: staging.anuncios (host_is_superhost, review_scores_rating) e staging.calendario. Anúncios sem nota ficam fora da média de nota (contados em anuncios_com_nota).
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.superhost AS
WITH cal AS (
    SELECT listing_id,
           count(*) FILTER (WHERE NOT available) AS dias_indisponiveis,
           count(*) AS dias
    FROM staging.calendario
    GROUP BY 1
)
SELECT a.host_is_superhost AS superhost,
       count(*) AS anuncios,
       count(a.review_scores_rating) AS anuncios_com_nota,
       round(avg(a.review_scores_rating), 2) AS nota_media,
       round(100.0 * sum(c.dias_indisponiveis) / sum(c.dias), 2) AS taxa_ocupacao_pct
FROM staging.anuncios a
JOIN cal c ON c.listing_id = a.id
GROUP BY 1
ORDER BY 1;
