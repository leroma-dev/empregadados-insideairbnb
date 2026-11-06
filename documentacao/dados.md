# Dados

## Fontes

Os quatro arquivos do Inside Airbnb para o Rio de Janeiro:

| Arquivo | Tabela no banco | Linhas |
|---|---|---|
| `listings` (anúncios) | `raw.anuncios` | 48.247 |
| `calendar` (calendário) | `raw.calendario` | 17.610.155 |
| `reviews` (avaliações) | `raw.avaliacoes` | 1.461.658 |
| `neighbourhoods` (bairros) | `raw.bairros` | 160 |

## Relações entre as tabelas

- Cada avaliação pertence a um anúncio (`avaliacoes.listing_id` referencia
  `anuncios.id`).
- Cada dia do calendário pertence a um anúncio (`calendario.listing_id`
  referencia `anuncios.id`).
- Cada anúncio está em um bairro (`anuncios.neighbourhood_cleansed` referencia
  `bairros.neighbourhood`).

## Tabelas do schema `mart`

| Tabela | O que guarda |
|---|---|
| `mart.preco_bairro` | Preço médio e mediano da diária por bairro. |
| `mart.ocupacao_bairro` | Taxa de ocupação estimada por bairro. |
| `mart.receita_mensal_anuncio` | Receita potencial por anúncio e por mês. |
| `mart.multi_host` | Anfitriões com mais de um imóvel. |
| `mart.reviews_mensal` | Número de avaliações por mês, em todo o histórico. |
| `mart.sazonalidade_reviews` | Média de avaliações por mês do ano. |
| `mart.inteiro_vs_privado` | Preço do imóvel inteiro e do quarto privado. |
| `mart.superhost` | Nota e ocupação de superhosts e demais anfitriões. |
| `mart.amenities` | Correlação entre o número de comodidades, o preço e a nota. |
