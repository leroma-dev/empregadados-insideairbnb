# Pipeline de Dados – Airbnb Rio de Janeiro

Exercício de tratamento de dados: ingestão, limpeza, transformação e
criação de indicadores a partir dos dados públicos do Inside Airbnb.

## Fonte dos dados

| | |
|---|---|
| **Fonte** | [Inside Airbnb](https://insideairbnb.com) |
| **Licença** | [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) |
| **Cidade** | Rio de Janeiro, RJ, Brasil |
| **Snapshot** | AAAA-MM-DD <!-- substitua pela data usada --> |

> Dados: Inside Airbnb (insideairbnb.com), licença CC BY 4.0, snapshot de AAAA-MM-DD.
> Os dados foram transformados (limpeza de tipos, tratamento de nulos e agregações) para este exercício.

Este projeto não tem vínculo com o Airbnb nem com o Inside Airbnb.

## Tabelas utilizadas

| Arquivo | Descrição | Chave |
|---|---|---|
| `listings.csv.gz` | Anúncios (1 linha por imóvel) | `id` |
| `calendar.csv.gz` | Disponibilidade e preço diário | `listing_id` → `listings.id` |
| `reviews.csv.gz` | Avaliações dos hóspedes | `listing_id` → `listings.id` |
| `neighbourhoods.csv` | Bairros | `neighbourhood` → `listings.neighbourhood_cleansed` |

## Como obter os dados

Os arquivos brutos **não são versionados** (ver `.gitignore`) por causa do tamanho.
Para baixá-los:

```bash
python scripts/download_data.py --snapshot AAAA-MM-DD
```

As datas disponíveis estão em <https://insideairbnb.com/get-the-data/>.
Os arquivos são salvos em `data/raw/`.

## Estrutura

```
.
├── data/
│   ├── raw/        # dados baixados, sem alteração (ignorado no git)
│   ├── staging/    # dados limpos e tipados (gerado)
│   └── mart/       # tabelas analíticas / indicadores (gerado)
├── scripts/
│   └── download_data.py
├── .gitignore
└── README.md
```
