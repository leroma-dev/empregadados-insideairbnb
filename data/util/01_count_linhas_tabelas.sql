SELECT *, anuncios + calendario + avaliacoes + bairros AS total
FROM (
  SELECT
    (SELECT count(*) FROM raw.anuncios)   AS anuncios,
    (SELECT count(*) FROM raw.calendario) AS calendario,
    (SELECT count(*) FROM raw.avaliacoes) AS avaliacoes,
    (SELECT count(*) FROM raw.bairros)    AS bairros
);
