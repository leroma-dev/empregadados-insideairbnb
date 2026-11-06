-- Mart: mart.inteiro_vs_privado
-- Pergunta 6: imóvel inteiro versus quarto privado (preço).
-- Contexto: Fonte: staging.anuncios (room_type, price). Compara Entire home/apt com Private room; diferença percentual na análise. Exclui anúncios sem preço.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.inteiro_vs_privado AS
SELECT room_type AS tipo,
       count(*) AS anuncios,
       round(avg(price), 2) AS preco_medio,
       round(quantile_cont(CAST(price AS DOUBLE), 0.5), 2) AS preco_mediano
FROM staging.anuncios
WHERE price IS NOT NULL
  AND room_type IN ('Entire home/apt', 'Private room')
GROUP BY 1
ORDER BY 1;
