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

## Relatório de testes

Gerado com `scripts/comandos_uv.sh test` (pytest com cobertura sobre `src/`).

**Resultado: 97 testes passaram, 0 falharam** (tempo: cerca de 9 s).

Cobertura por módulo:

| Módulo | Cobertura | Linhas sem teste |
|---|---|---|
| `src/pipeline/db.py` | 100% | – |
| `src/pipeline/publicacao.py` | 98% | 82 |
| `src/pipeline/marts.py` | 96% | 77, 94, 169 |
| `src/pipeline/ingestao.py` | 95% | 129, 152, 193 |
| `src/pipeline/staging.py` | 94% | 328-332, 342, 353 |
| `src/dashboard/preparo.py` | 93% | 21, 51 |
| `src/dashboard/dados_ui.py` | 83% | 12 |
| `src/dashboard/dados.py` | 81% | 52, 57, 78-79, 90-96 |
| `src/dashboard/app.py` | 70% | 11, 31, 40, 53-67, 71 |
| `src/dashboard/graficos.py` | 39% | 13-14, 19-27 |
| `src/dashboard/paginas/anfitriao.py` | 25% | 11-30 |
| `src/dashboard/paginas/investidor.py` | 14% | 11-50 |
| `src/ui/ui.py` | 84% | 66-67, 76-78, 97 |
| **Total** | **82%** | 102 de 568 linhas |

O que está fora da cobertura: as páginas do Streamlit (`paginas/`, `graficos.py`)
e a parte de desenho de `app.py` não têm teste de renderização. Eles são
conferidos pelas funções de preparação, que têm teste, e por checagem manual
do app.
