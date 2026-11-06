# Spec da etapa 2: staging (insideairbnb)

Status: APROVADA. Não há pontos [DECIDIR] em aberto.

Escrito para: quem vai construir a etapa 2 e conferir o resultado depois.

## CONTEXTO

A etapa 1 guardou o dado que chegou, em `raw`, tudo como texto (`VARCHAR`),
com campo vazio gravado como NULL. A etapa 2 é onde cada conversão de tipo e
cada limpeza viram uma decisão registrada. Esta spec é essa lista de decisões.

A fronteira é: `raw` = o que chegou; `staging` = o que decidimos. Nada é
corrigido na etapa 1.

## STACK

- Python 3.13, dependências gerenciadas com uv.
- DuckDB, arquivo `data/insideairbnb.duckdb`.
- pandas, apenas para a leitura da etapa 1; a etapa 2 não traz dados para o
  pandas.
- Conversões em SQL no DuckDB (`CAST`, `DECIMAL`, `strptime` quando preciso),
  disparadas pelo Python. O dado já está no banco; não há motivo para trazê-lo
  para a memória só para converter tipo.
- Nenhum orquestrador. Script executável pela linha de comando.
- pytest e ruff, como na etapa 1.

## O QUE JÁ EXISTE (use, não reimplemente)

Recursos criados na etapa 1.

`src/pipeline/db.py`:

- `caminho_banco() -> Path`: caminho de `data/insideairbnb.duckdb`, independente
  da pasta corrente.
- `conectar() -> duckdb.DuckDBPyConnection`: abre o banco, cria a pasta `data`
  se faltar, cria o schema `raw` e define `memory_limit = '2GB'`.
- `gravar(con, nome_qualificado, df) -> int`: `CREATE OR REPLACE TABLE` a partir
  de um DataFrame.
- `anexar(con, nome_qualificado, df) -> None`: `INSERT INTO` a partir de um
  DataFrame.

`src/pipeline/ingestao.py`:

- `MAPA`: arquivo -> tabela raw (`listings.csv.gz` -> `raw.anuncios`, etc.).
- `ingerir(con, pasta)`: grava as quatro tabelas numa única transação.
- `formatar_contagem(n) -> str`: milhar com ponto.

Schema `raw`, quatro tabelas, todas as colunas `VARCHAR`:

| Tabela | Linhas |
|---|---|
| `raw.anuncios` | 48.247 |
| `raw.calendario` | 17.610.155 |
| `raw.avaliacoes` | 1.461.658 |
| `raw.bairros` | 160 |

Relações confirmadas nos dados brutos (ver `docs/spec/05_er_raw.md`):

- Todos os 48.247 anúncios têm `neighbourhood_cleansed` presente em
  `bairros.neighbourhood`.
- Todas as avaliações têm `listing_id` presente em `anuncios.id`.

## ARTEFATOS A PRODUZIR

Esta seção é o conteúdo da spec da etapa 2: o que será criado nesta etapa.

Entregáveis:

- `src/pipeline/staging.py`, executável com `uv run python -m pipeline.staging`.
- Schema `staging` com quatro tabelas: `staging.anuncios`, `staging.calendario`,
  `staging.avaliacoes`, `staging.bairros`.
- Testes em `tests/test_staging.py`, usando `tmp_path`; nunca tocam em
  `data/raw/` nem no `.duckdb` real.

### Escopo

Quatro tabelas no schema `staging`, uma para cada tabela de `raw`:

| Origem (raw) | Destino (staging) |
|---|---|
| `raw.anuncios` | `staging.anuncios` |
| `raw.calendario` | `staging.calendario` |
| `raw.avaliacoes` | `staging.avaliacoes` |
| `raw.bairros` | `staging.bairros` |

Fora de escopo: indicadores e tabelas de `mart`; dashboard; documentação.

### Regras gerais

R1. Nenhuma linha de `raw` some em silêncio. Linhas só saem pela regra de
DUPLICATAS (linha inteira repetida), e cada saída é contada.
Motivo: contagem que some sem registro impede conferir o resultado depois.

R2. Nenhuma linha é apagada por ter nulo, e nenhum nulo é preenchido.
CONVERSÃO QUE FALHA: para tudo. Usar `strptime` e `CAST`, que estouram; nunca
`try_strptime`, `TRY_CAST` ou qualquer conversão que transforme falha em
nulo. Ao falhar, dizer tabela, coluna e um exemplo do valor que não converteu,
e encerrar com `sys.exit(1)`. Motivo: um nulo fabricado pela conversão fica
indistinguível de um nulo verdadeiro do dado, para sempre.

R3. Reexecução: cada tabela é recriada com `CREATE OR REPLACE`, a partir de
`raw`. Rodar duas vezes dá o mesmo resultado.
Motivo: reexecutar não pode acumular linhas nem mudar o resultado.

R4. Todas as tabelas de `staging` são gravadas numa única transação, como na
ingestão. Se qualquer tabela falhar, nenhuma das quatro é alterada.
Motivo: nunca deixar `staging` meio atualizado, com algumas tabelas novas e
outras antigas.

R5. Nenhum valor é trocado por um "plausível". Preço zero ou data inválida não
viram outra coisa. Esses casos ficam como estão, ou são tratados pela regra
explícita da coluna.
Motivo: um valor inventado parece dado real e some na análise.

R6. Texto vazio em `raw` vira NULL em `staging` nas colunas que não são texto.
Colunas de texto mantêm o texto como está, salvo regra explícita da coluna
(ver `staging.bairros`).
Motivo: em coluna numérica ou de data, vazio não é um valor; guardá-lo como
texto quebraria as conversões e as somas.

### Relacionamentos

- `raw.anuncios.id` ↔ `raw.avaliacoes.listing_id`: cada avaliação pertence a um
  anúncio. Em `staging`, a verificação é critério de aceite: nenhum
  `staging.avaliacoes.listing_id` pode faltar em `staging.anuncios.id`.
- `raw.anuncios.id` ↔ `raw.calendario.listing_id`: mesma verificação para o
  calendário.
- `raw.bairros.neighbourhood` ↔ `raw.anuncios.neighbourhood_cleansed`: mesma
  verificação.

Nenhuma dessas relações é imposta por constraint nesta etapa; a verificação é
feita como critério de aceite.

### Duplicatas

Chave de cada tabela (o que identifica uma linha):

| Tabela | Chave | Tipo da chave |
|---|---|---|
| `staging.anuncios` | (`id`) | PK |
| `staging.bairros` | (`neighbourhood`) | PK |
| `staging.calendario` | (`listing_id`, `date`) | PK natural, FK de `listing_id` para `anuncios.id` |
| `staging.avaliacoes` | (`id`, `listing_id`) | PK natural; `listing_id` é FK para `anuncios.id` |

Regras:

- Linha inteira repetida (todas as colunas iguais, NULL igual a NULL): mantém
  uma, e conta quantas saíram.
- Chave repetida com conteúdo diferente: para, mostra a chave e as linhas
  conflitantes, e encerra com `sys.exit(1)`. Não escolhe uma por conta própria.

Motivo: escolher em silêncio é decidir sem dizer que decidiu.

Situação medida: em `avaliacoes`, nenhuma linha é idêntica a outra (0 saídas).
A chave (`id`, `listing_id`) é única em todas as linhas. Em `anuncios`,
`bairros` e `calendario`, a unicidade da chave ainda não foi verificada nos
dados; entra como critério de aceite.

### Regras por tabela

#### staging.avaliacoes

Origem: `raw.avaliacoes` (1.461.658 linhas; 1.453.490 valores distintos em `id`).

- `listing_id` → BIGINT. Chave de ligação com `staging.anuncios.id`.
- `id` → BIGINT.
- `date` → DATE (formato AAAA-MM-DD; sem valores vazios nos dados atuais).
- `reviewer_id` → BIGINT.
- `reviewer_name`, `comments` → VARCHAR, sem alteração.

`id` não é único: há 1.769 valores repetidos, cobrindo 9.937 linhas (8.168
linhas "a mais"). Dentro de cada `id` repetido, `date`, `reviewer_id`,
`reviewer_name` e `comments` são iguais; só `listing_id` muda. Uma avaliação
ligada a mais de um anúncio é dado legítimo, não duplicata.

Regra: aplica-se a seção DUPLICATAS. Não há linha idêntica em todas as colunas
(medido: 0), então nenhuma linha sai. A chave natural (`id`, `listing_id`) é
única em todas as 1.461.658 linhas; essa unicidade é critério de aceite.

Consultas de verificação: `data/util/02_registros_duplicados_raw_avaliacoes.sql`.

#### staging.anuncios

Origem: `raw.anuncios` (48.247 linhas; `id` é único).

Todas as colunas de `raw.anuncios` entram em `staging.anuncios`. As colunas com
regra explícita abaixo recebem o tipo indicado; as demais ficam VARCHAR, sem
conversão.

- `id`, `host_id`, `scrape_id` → BIGINT.
- `latitude`, `longitude` → DOUBLE.
- `price` → DECIMAL(10,2). O raw tem valores como `$314.00`. Regra: remover `$`
  e separador de milhar; vazio vira NULL. O valor é mantido na moeda de
  publicação (USD); não há conversão de moeda.
  Motivo do tipo: DOUBLE não representa centavos com exatidão, e soma de
  dinheiro tem que fechar.
- `host_is_superhost`, `host_identity_verified`, `instant_bookable` → BOOLEAN
  (`t` → true, `f` → false, vazio → NULL).
- `host_since`, `first_review`, `last_review` → DATE (vazio → NULL).
- `number_of_reviews`, `accommodates`, `minimum_nights`, `maximum_nights`,
  `availability_365` → INTEGER.
- `review_scores_rating` e similares → DOUBLE.

#### staging.calendario

Origem: `raw.calendario` (17.610.155 linhas).

- `listing_id` → BIGINT.
- `date` → DATE.
- `available` → BOOLEAN (`t` → true, `f` → false).
  Motivo: `t`/`f` é código, não texto livre; BOOLEAN aceita só os dois valores.
- `minimum_nights`, `maximum_nights` → INTEGER.

Chave natural: (`listing_id`, `date`). Não é imposta por constraint nesta
etapa; a verificação de unicidade entra como critério de aceite.

#### staging.bairros

Origem: `raw.bairros` (160 linhas).

- `neighbourhood` → VARCHAR, sem alteração.
- `neighbourhood_group` → VARCHAR. Campo vazio vira NULL. Esta regra vale para
  esta coluna mesmo sendo texto (exceção explícita à R6).

#### Datas

- Datas sem hora (`date`, `host_since`, `first_review`, `last_review`) → DATE.
  Motivo: a origem traz só o dia; guardar hora seria inventar precisão.
- Nenhuma coluna de `raw.anuncios`, `raw.calendario`, `raw.avaliacoes` ou
  `raw.bairros` tem data com hora; o TIMESTAMP definido para a etapa do Olist
  não se aplica aqui.

### Critérios de aceite

Contagens e chaves

- CA1. Para cada tabela: `count(*)` em `staging` = `count(*)` em `raw` − linhas
  removidas pela regra de DUPLICATAS (o número sai na tela).
- CA2. Em `staging.avaliacoes`, nos dados atuais, o número de linhas removidas é
  0 e o total é 1.461.658.
- CA3. Chave única em `staging`: `count(*) − count(DISTINCT chave) = 0` para
  `anuncios` (`id`), `bairros` (`neighbourhood`), `calendario`
  (`listing_id`, `date`) e `avaliacoes` (`id`, `listing_id`).
- CA4. Chave repetida com conteúdo diferente (teste com fixture): a execução
  para com `sys.exit(1)`, mostra a chave e as linhas conflitantes, e nenhuma
  tabela é alterada (R4).

Tipos e valores

- CA5. `DESCRIBE staging.<tabela>` bate com a seção Definições estruturadas.
- CA6. Nulos por coluna: para toda coluna, nulos em `staging` = nulos em
  `raw`. O `raw` já grava campo vazio como NULL, então a conversão de vazio
  não acrescenta nulo.
- CA7. `price`: nenhum valor da origem com mais de 2 casas decimais e nenhum
  valor acima de 99.999.999,99 (limite de DECIMAL(10,2)). Se houver, a
  execução para com erro (R2), e não arredonda em silêncio.
  Situação medida em `raw.anuncios.price`: 44.147 valores não nulos, todos no
  padrão `$9,999.99`; todos com exatamente 2 casas decimais; maior valor
  587.008,00; nenhum acima do limite. Nos dados atuais, DECIMAL(10,2) não
  altera nenhum valor.
- CA8. Booleanos (`host_is_superhost`, `host_identity_verified`,
  `instant_bookable`, `available`): só `t`, `f` ou NULL. Outro valor para a
  execução com erro (R2).
- CA9. Datas (`date`, `host_since`, `first_review`, `last_review`): só
  `AAAA-MM-DD` ou NULL. Outro valor para a execução com erro (R2).
- CA10. Conversão que falha (teste com fixture): a execução para com
  `sys.exit(1)`, a mensagem diz tabela, coluna e um exemplo do valor, e nenhuma
  das quatro tabelas é alterada (R4).

Relações

- CA11. Órfãos = 0: nenhum `staging.avaliacoes.listing_id` sem `anuncios.id`;
  nenhum `staging.calendario.listing_id` sem `anuncios.id`; nenhum
  `staging.anuncios.neighbourhood_cleansed` sem `bairros.neighbourhood`.
  Verificado com LEFT JOIN ... IS NULL.

Reexecução e saída

- CA12. Duas execuções seguidas: saída idêntica e contagens idênticas.
- CA13. Rodar dez vezes dá o mesmo resultado que rodar uma (`CREATE OR REPLACE`).
- CA14. Saída no formato da seção SAÍDA NA TELA: uma linha por tabela, linha
  de nulos mantidos abaixo, linha final de total, milhar com ponto, stdout em
  utf-8.
- CA15. Tabela de `raw` faltando: a execução lista a faltante, manda rodar o
  comando de ingestão, encerra com `sys.exit(1)`, e não cria tabela de `staging`.

Testes

- CA16. Testes em `tests/test_staging.py` com `tmp_path`; nunca tocam em
  `data/raw/` nem no `.duckdb` real.

## Definições estruturadas

Formato: `PK` marca chave primária e `FK` marca chave estrangeira. Para cada
entidade, a linha de nível 1 traz a tabela em `raw` e a tabela em `staging`;
os campos abaixo trazem `campo tipo` em `raw` → `campo tipo` em `staging`.
Campo sem mudança de tipo é `VARCHAR → VARCHAR`. Todas as colunas de `raw`
são `VARCHAR`.

**Entidade: Bairro**

- raw.bairros - staging.bairros
  - PK `neighbourhood` VARCHAR → PK `neighbourhood` VARCHAR
  - `neighbourhood_group` VARCHAR → `neighbourhood_group` VARCHAR (vazio → NULL)

**Entidade: Anúncio**

- raw.anuncios - staging.anuncios
  - PK `id` VARCHAR → PK `id` BIGINT
  - `listing_url` VARCHAR → `listing_url` VARCHAR
  - `scrape_id` VARCHAR → `scrape_id` BIGINT
  - `last_scraped` VARCHAR → `last_scraped` VARCHAR
  - `source` VARCHAR → `source` VARCHAR
  - `name` VARCHAR → `name` VARCHAR
  - `description` VARCHAR → `description` VARCHAR
  - `neighborhood_overview` VARCHAR → `neighborhood_overview` VARCHAR
  - `picture_url` VARCHAR → `picture_url` VARCHAR
  - `host_id` VARCHAR → `host_id` BIGINT
  - `host_url` VARCHAR → `host_url` VARCHAR
  - `host_profile_id` VARCHAR → `host_profile_id` VARCHAR
  - `host_profile_url` VARCHAR → `host_profile_url` VARCHAR
  - `host_name` VARCHAR → `host_name` VARCHAR
  - `host_since` VARCHAR → `host_since` DATE
  - `hosts_time_as_user_years` VARCHAR → `hosts_time_as_user_years` VARCHAR
  - `hosts_time_as_user_months` VARCHAR → `hosts_time_as_user_months` VARCHAR
  - `hosts_time_as_host_years` VARCHAR → `hosts_time_as_host_years` VARCHAR
  - `hosts_time_as_host_months` VARCHAR → `hosts_time_as_host_months` VARCHAR
  - `host_location` VARCHAR → `host_location` VARCHAR
  - `host_about` VARCHAR → `host_about` VARCHAR
  - `host_response_time` VARCHAR → `host_response_time` VARCHAR
  - `host_response_rate` VARCHAR → `host_response_rate` VARCHAR
  - `host_acceptance_rate` VARCHAR → `host_acceptance_rate` VARCHAR
  - `host_is_superhost` VARCHAR → `host_is_superhost` BOOLEAN
  - `host_thumbnail_url` VARCHAR → `host_thumbnail_url` VARCHAR
  - `host_picture_url` VARCHAR → `host_picture_url` VARCHAR
  - `host_neighbourhood` VARCHAR → `host_neighbourhood` VARCHAR
  - `host_listings_count` VARCHAR → `host_listings_count` VARCHAR
  - `host_total_listings_count` VARCHAR → `host_total_listings_count` VARCHAR
  - `host_verifications` VARCHAR → `host_verifications` VARCHAR
  - `host_has_profile_pic` VARCHAR → `host_has_profile_pic` VARCHAR
  - `host_identity_verified` VARCHAR → `host_identity_verified` BOOLEAN
  - `neighbourhood` VARCHAR → `neighbourhood` VARCHAR
  - FK `neighbourhood_cleansed` VARCHAR → FK `neighbourhood_cleansed` VARCHAR (referencia `bairros.neighbourhood`)
  - `neighbourhood_group_cleansed` VARCHAR → `neighbourhood_group_cleansed` VARCHAR
  - `latitude` VARCHAR → `latitude` DOUBLE
  - `longitude` VARCHAR → `longitude` DOUBLE
  - `property_type` VARCHAR → `property_type` VARCHAR
  - `room_type` VARCHAR → `room_type` VARCHAR
  - `accommodates` VARCHAR → `accommodates` INTEGER
  - `bathrooms` VARCHAR → `bathrooms` VARCHAR
  - `bathrooms_text` VARCHAR → `bathrooms_text` VARCHAR
  - `bedrooms` VARCHAR → `bedrooms` VARCHAR
  - `beds` VARCHAR → `beds` VARCHAR
  - `amenities` VARCHAR → `amenities` VARCHAR
  - `price` VARCHAR → `price` DECIMAL(10,2)
  - `price_quote_checkin_date` VARCHAR → `price_quote_checkin_date` VARCHAR
  - `price_quote_checkout_date` VARCHAR → `price_quote_checkout_date` VARCHAR
  - `price_quote_total_price` VARCHAR → `price_quote_total_price` VARCHAR
  - `price_quote_price_per_night` VARCHAR → `price_quote_price_per_night` VARCHAR
  - `price_quote_raw` VARCHAR → `price_quote_raw` VARCHAR
  - `minimum_nights` VARCHAR → `minimum_nights` INTEGER
  - `maximum_nights` VARCHAR → `maximum_nights` INTEGER
  - `minimum_minimum_nights` VARCHAR → `minimum_minimum_nights` VARCHAR
  - `maximum_minimum_nights` VARCHAR → `maximum_minimum_nights` VARCHAR
  - `minimum_maximum_nights` VARCHAR → `minimum_maximum_nights` VARCHAR
  - `maximum_maximum_nights` VARCHAR → `maximum_maximum_nights` VARCHAR
  - `minimum_nights_avg_ntm` VARCHAR → `minimum_nights_avg_ntm` VARCHAR
  - `maximum_nights_avg_ntm` VARCHAR → `maximum_nights_avg_ntm` VARCHAR
  - `calendar_updated` VARCHAR → `calendar_updated` VARCHAR
  - `has_availability` VARCHAR → `has_availability` VARCHAR
  - `availability_30` VARCHAR → `availability_30` VARCHAR
  - `availability_60` VARCHAR → `availability_60` VARCHAR
  - `availability_90` VARCHAR → `availability_90` VARCHAR
  - `availability_365` VARCHAR → `availability_365` INTEGER
  - `calendar_last_scraped` VARCHAR → `calendar_last_scraped` VARCHAR
  - `number_of_reviews` VARCHAR → `number_of_reviews` INTEGER
  - `number_of_reviews_ltm` VARCHAR → `number_of_reviews_ltm` VARCHAR
  - `number_of_reviews_l30d` VARCHAR → `number_of_reviews_l30d` VARCHAR
  - `availability_eoy` VARCHAR → `availability_eoy` VARCHAR
  - `number_of_reviews_ly` VARCHAR → `number_of_reviews_ly` VARCHAR
  - `estimated_occupancy_l365d` VARCHAR → `estimated_occupancy_l365d` VARCHAR
  - `estimated_revenue_l365d` VARCHAR → `estimated_revenue_l365d` VARCHAR
  - `first_review` VARCHAR → `first_review` DATE
  - `last_review` VARCHAR → `last_review` DATE
  - `review_scores_rating` VARCHAR → `review_scores_rating` DOUBLE
  - `review_scores_accuracy` VARCHAR → `review_scores_accuracy` DOUBLE
  - `review_scores_cleanliness` VARCHAR → `review_scores_cleanliness` DOUBLE
  - `review_scores_checkin` VARCHAR → `review_scores_checkin` DOUBLE
  - `review_scores_communication` VARCHAR → `review_scores_communication` DOUBLE
  - `review_scores_location` VARCHAR → `review_scores_location` DOUBLE
  - `review_scores_value` VARCHAR → `review_scores_value` DOUBLE
  - `license` VARCHAR → `license` VARCHAR
  - `instant_bookable` VARCHAR → `instant_bookable` BOOLEAN
  - `calculated_host_listings_count` VARCHAR → `calculated_host_listings_count` VARCHAR
  - `calculated_host_listings_count_entire_homes` VARCHAR → `calculated_host_listings_count_entire_homes` VARCHAR
  - `calculated_host_listings_count_private_rooms` VARCHAR → `calculated_host_listings_count_private_rooms` VARCHAR
  - `calculated_host_listings_count_shared_rooms` VARCHAR → `calculated_host_listings_count_shared_rooms` VARCHAR
  - `reviews_per_month` VARCHAR → `reviews_per_month` VARCHAR

**Entidade: Calendário**

- raw.calendario - staging.calendario
  - PK FK `listing_id` VARCHAR → PK FK `listing_id` BIGINT (PK natural com `date`, não imposta; FK referencia `anuncios.id`)
  - PK `date` VARCHAR → PK `date` DATE (PK natural com `listing_id`, não imposta)
  - `available` VARCHAR → `available` BOOLEAN
  - `minimum_nights` VARCHAR → `minimum_nights` INTEGER
  - `maximum_nights` VARCHAR → `maximum_nights` INTEGER

**Entidade: Avaliação**

- raw.avaliacoes - staging.avaliacoes
  - FK `listing_id` VARCHAR → FK `listing_id` BIGINT (referencia `anuncios.id`)
  - PK (natural, com `listing_id`) `id` VARCHAR → PK (natural, com `listing_id`) `id` BIGINT
  - `date` VARCHAR → `date` DATE
  - `reviewer_id` VARCHAR → `reviewer_id` BIGINT
  - `reviewer_name` VARCHAR → `reviewer_name` VARCHAR
  - `comments` VARCHAR → `comments` VARCHAR

## Decisões pendentes

Decididas nesta versão:

- Valor não convertível: para com erro, `sys.exit(1)`, sem NULL fabricado (R2).
  Muda a decisão anterior de NULL + auditoria, que foi revista.
- Datas sem hora: DATE. Nenhuma coluna das quatro tabelas tem data com hora.
- Duplicatas em `avaliacoes`: nenhuma linha removida; chave natural
  (`id`, `listing_id`), única nos dados atuais.
- Moeda e formato de `price`: DECIMAL(10,2), moeda de publicação (USD), sem
  conversão.
- Colunas de `anuncios` que entram no staging: todas.
- `neighbourhood_group` vazio: NULL.
- Nulos: nenhuma linha apagada por ter nulo; nenhum nulo preenchido.

Nenhuma pendente.

SAÍDA NA TELA
   Uma linha por tabela, no formato:
     staging.tabela  qtd de linhas ( qtd linhas duplicatas)
   Abaixo dela, indentadas, as colunas com nulo e a contagem:
       nulos mantidos: coluna1 qtd1, coluna2 qtd2, coluna3 qtd3
   As contagens vêm do banco, milhar separado por ponto. Linha final com o
   total. stdout reconfigurado para utf-8.

REEXECUÇÃO
   CREATE OR REPLACE TABLE, nunca acrescenta. Rodar dez vezes = rodar uma.

ERRO
   Antes de transformar, verifica se as tabelas de entrada existem em
   raw. Faltando qualquer uma: lista quais, diz para rodar o comando de ingestao
   e encerra com sys.exit(1).



## Premissas assumidas

Itens que não estavam escritos na spec original e foram assumidos na
construção. Confirmados pelo autor da spec.

- O artefato é `src/pipeline/staging.py`, executado com
  `uv run python -m pipeline.staging`, no mesmo padrão de `ingestao`.
- As conversões são SQL no DuckDB; o pandas não participa da etapa 2.
- As colunas de `raw.anuncios` mantêm o nome original em `staging`; nenhuma é
  renomeada.
- Colunas de `anuncios` sem regra explícita ficam VARCHAR, sem conversão. Isso
  vale também para colunas numéricas como `bedrooms`, `bathrooms` e
  `reviews_per_month`.
- `review_scores_*` (as sete colunas) viram DOUBLE. A spec dizia "rating e
  similares".
- `anuncios.neighbourhood_group_cleansed` não tem regra e não é o mesmo campo
  que `bairros.neighbourhood_group`.
- Linha inteira repetida é comparada com todas as colunas, tratando NULL como
  igual a NULL.
- A ordem das tabelas na saída é a do escopo: anuncios, calendario, avaliacoes,
  bairros.
- O TIMESTAMP da lista do Olist não entra nesta etapa, pois nenhuma coluna do
  Inside Airbnb tem data com hora.

## Entregáveis de código (regras de entrega)

- `src/pipeline/staging.py` começa com docstring que resume esta spec e dá o
  motivo de cada regra, não só o que ela manda fazer.
- Comentários no código apenas onde a decisão não é óbvia pelo próprio código.


