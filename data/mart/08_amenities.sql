-- Mart: mart.amenities
-- Pergunta 8: relação entre a quantidade de amenities e o preço ou a nota.
-- Contexto: Fonte: staging.anuncios (amenities, price, review_scores_rating). Quantidade = itens da lista JSON em amenities. Correlação de Pearson.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.amenities AS
WITH am AS (
    SELECT price,
           review_scores_rating,
           json_array_length(CAST(amenities AS JSON)) AS qtd_amenities
    FROM staging.anuncios
    WHERE amenities IS NOT NULL
)
SELECT count(*) AS anuncios,
       round(corr(qtd_amenities, CAST(price AS DOUBLE)), 3) AS corr_qtd_preco,
       round(corr(qtd_amenities, review_scores_rating), 3) AS corr_qtd_nota
FROM am;
