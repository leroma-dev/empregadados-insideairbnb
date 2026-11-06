-- Mart: mart.receita_mensal_anuncio
-- Pergunta 3: receita potencial mensal por anúncio (preço x dias ocupados).
-- Contexto: Fonte: staging.calendario e staging.anuncios. Preço do anúncio para o ano inteiro (o calendário não tem preço por dia). Exclui anúncios sem preço.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.receita_mensal_anuncio AS
SELECT a.id AS listing_id,
       date_trunc('month', c.date) AS mes,
       count(*) FILTER (WHERE NOT c.available) AS dias_ocupados,
       round(a.price * count(*) FILTER (WHERE NOT c.available), 2) AS receita_potencial
FROM staging.calendario c
JOIN staging.anuncios a ON a.id = c.listing_id
WHERE a.price IS NOT NULL
GROUP BY a.id, a.price, 2
ORDER BY 1, 2;
