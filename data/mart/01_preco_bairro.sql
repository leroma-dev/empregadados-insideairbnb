-- Mart: mart.preco_bairro
-- Pergunta 1: preço médio e mediano da diária por bairro.
-- Contexto: Fonte: staging.anuncios (price, neighbourhood_cleansed). Exclui anúncios sem preço.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.preco_bairro AS
SELECT neighbourhood_cleansed AS bairro,
       count(price) AS anuncios_com_preco,
       round(avg(price), 2) AS preco_medio,
       round(quantile_cont(CAST(price AS DOUBLE), 0.5), 2) AS preco_mediano
FROM staging.anuncios
WHERE price IS NOT NULL
GROUP BY 1
ORDER BY 1;
