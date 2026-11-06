/*
nenhuma linha de raw.avaliacoes é idêntica a outra. A recomendação (b) da spec remove zero linhas. O problema real é outro: o id não identifica a avaliação sozinho. Ele identifica a avaliação junto com o listing_id.

Números (medidos em raw.avaliacoes, 1.461.658 linhas):

Linhas idênticas em todas as colunas a remover: 0.
Valores de id que aparecem mais de uma vez: 1.769, cobrindo 9.937 linhas. São 8.168 linhas "a mais" (9.937 − 1.769), o mesmo número citado na spec.
Dentro desses 1.769 ids, date, reviewer_id, reviewer_name e comments são sempre iguais. Só listing_id muda.
O par (id, listing_id) é único em todas as linhas: 1.461.658 pares distintos.
Critério de identidade: duas linhas são idênticas quando todas as colunas são iguais, com NULL tratado como igual a NULL. Pelo que vimos, a regra correta não é essa. A chave natural é (id, listing_id). Uma avaliação pode estar ligada a mais de um anúncio, e isso é dado legítimo, não duplicata.


*/


-- Linhas idênticas em todas as colunas (NULL = NULL)
SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM raw.avaliacoes)) AS linhas_identicas_a_remover
FROM raw.avaliacoes;

-- Ids repetidos e quais colunas mudam dentro de cada id
WITH g AS (SELECT id FROM raw.avaliacoes GROUP BY id HAVING count(*) > 1)
SELECT
  count(*) AS grupos,
  count(*) FILTER (WHERE n_listing > 1) AS listing_muda,
  count(*) FILTER (WHERE n_date > 1)    AS date_muda,
  count(*) FILTER (WHERE n_reviewer > 1) AS reviewer_muda,
  count(*) FILTER (WHERE n_comments > 1) AS comentario_muda
FROM (
  SELECT a.id,
         count(DISTINCT listing_id) AS n_listing,
         count(DISTINCT date) AS n_date,
         count(DISTINCT reviewer_id) AS n_reviewer,
         count(DISTINCT comments) AS n_comments
  FROM raw.avaliacoes a JOIN g USING (id)
  GROUP BY a.id
);

-- Unicidade da chave natural (id, listing_id)
SELECT count(*) AS total,
       count(DISTINCT (id, listing_id)) AS pares_distintos
FROM raw.avaliacoes;
