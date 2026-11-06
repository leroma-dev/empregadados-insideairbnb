-- Mart: mart.sazonalidade_reviews
-- Pergunta 5 (sazonalidade): média de reviews por mês do ano.
-- Contexto: Fonte: staging.avaliacoes (date). Para cada mês do ano, média das reviews dos anos em que o mês tem dados. Todo o histórico disponível; 2026 é incompleto.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.sazonalidade_reviews AS
WITH mensal AS (
    SELECT extract(year FROM date) AS ano,
           extract(month FROM date) AS mes_do_ano,
           count(*) AS reviews
    FROM staging.avaliacoes
    GROUP BY 1, 2
)
SELECT mes_do_ano,
       round(avg(reviews), 1) AS media_reviews_por_ano,
       count(*) AS anos_com_dados,
       sum(reviews) AS total_reviews
FROM mensal
GROUP BY 1
ORDER BY 1;
