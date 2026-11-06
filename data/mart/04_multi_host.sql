-- Mart: mart.multi_host
-- Pergunta 4: fatia de anfitriões com mais de um imóvel (multi-host).
-- Contexto: Fonte: staging.anuncios (host_id). Anfitrião = host_id; multi-host = mais de um anúncio.
-- Origem: docs/spec/08_mart_spec.md, seção PERGUNTAS E SQL.
-- Schema de saída: mart (recriado a cada execução; sem efeito sobre staging ou raw).

CREATE OR REPLACE TABLE mart.multi_host AS
WITH h AS (
    SELECT host_id, count(*) AS imoveis
    FROM staging.anuncios
    GROUP BY 1
)
SELECT count(*) AS anfitrioes,
       count(*) FILTER (WHERE imoveis > 1) AS multi_host,
       round(100.0 * count(*) FILTER (WHERE imoveis > 1) / count(*), 2) AS fatia_multi_host_pct,
       round(100.0 * sum(imoveis) FILTER (WHERE imoveis > 1) / sum(imoveis), 2) AS fatia_imoveis_multi_pct
FROM h;
