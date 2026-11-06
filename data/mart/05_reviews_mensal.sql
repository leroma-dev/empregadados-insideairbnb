-- Mart: mart.reviews_mensal
-- Pergunta 5: número de reviews por mês (série mensal completa).
-- Contexto: Fonte: staging.avaliacoes (date). Série mensal de todo o histórico disponível. Sazonalidade por mês do ano: arquivo 09.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.reviews_mensal AS
SELECT date_trunc('month', date) AS mes, count(*) AS reviews
FROM staging.avaliacoes
GROUP BY 1
ORDER BY 1;
