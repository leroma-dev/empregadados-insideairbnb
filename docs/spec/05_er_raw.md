# Diagrama entidade-relacionamento: camada raw

Escrito para: quem vai montar consultas e a etapa de staging sobre o schema `raw`.

Renderiza no GitHub e na extensão de Markdown do VS Code (Mermaid).

```mermaid
erDiagram
    BAIRROS ||--o{ ANUNCIOS : "tem anúncios em"
    ANUNCIOS ||--o{ CALENDARIO : "tem disponibilidade diária"
    ANUNCIOS ||--o{ AVALIACOES : "recebe"

    BAIRROS {
        string neighbourhood PK "160 valores, todos únicos"
        string neighbourhood_group
    }

    ANUNCIOS {
        string id PK "48.247 linhas, todas únicas"
        string host_id
        string neighbourhood_cleansed FK "referencia bairros.neighbourhood"
        string room_type
        string property_type
        string price "texto, ex.: $314.00"
        string latitude
        string longitude
        string number_of_reviews
        string availability_365
    }

    CALENDARIO {
        string listing_id FK "referencia anuncios.id"
        string date "AAAA-MM-DD"
        string available "t ou f"
        string minimum_nights
        string maximum_nights
    }

    AVALIACOES {
        string id "1.461.658 linhas, 1.453.490 valores distintos"
        string listing_id FK "referencia anuncios.id"
        string date
        string reviewer_id
        string reviewer_name
        string comments
    }
```

## Notas sobre as chaves

- **Relações confirmadas nos dados brutos:**
  - Todos os 48.247 anúncios têm `neighbourhood_cleansed` presente em `bairros.neighbourhood`.
  - Todas as avaliações têm `listing_id` presente em `anuncios.id`.
- **`calendario` não tem chave primária declarada.** A combinação (`listing_id`, `date`) deveria ser única, mas ainda não foi verificada nos 17,6 milhões de linhas.
- **`avaliacoes.id` não é único:** há 8.168 valores repetidos. Ver a decisão 1 em `docs/spec/06_staging_spec.md`.
- **Todas as colunas são texto** no `raw` (`VARCHAR`), inclusive as chaves. Os tipos só serão definidos na etapa de staging.
- `anuncios` tem 90 colunas no arquivo original. O diagrama mostra só as chaves e algumas colunas; a lista completa está em `data/raw/listings.csv.gz`.
