# Pipeline de Dados – Airbnb Rio de Janeiro

> **Dashboard:** https://empregadados-insideairbnb.streamlit.app/
> **Site da documentação:** https://leroma-dev.github.io/empregadados-insideairbnb/

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



## Empregados InsideAirbnb

Projeto de dados sobre os anúncios de Airbnb no Rio de Janeiro, a partir do
dataset público [Inside Airbnb](https://insideairbnb.com/). O projeto
transforma os arquivos brutos em indicadores e mostra esses indicadores num
painel para anfitriões e investidores.

### O que o projeto faz

1. **Ingestão:** lê os quatro arquivos brutos e grava no banco, sem alterar nada.
2. **Staging:** converte os tipos, remove linhas repetidas e valida os valores.
3. **Marts:** responde nove perguntas de negócio, uma tabela por pergunta.
4. **Publicação:** exporta os marts para arquivos Parquet, para o painel publicado.
5. **Dashboard:** duas páginas, Anfitrião e Investidor, com uma explicação em
   cada gráfico.

### Para quem é

- **Anfitriões:** para decidir preço e comparar o próprio imóvel com o bairro.
- **Investidores:** para decidir em que bairro entrar e qual receita esperar.

### Onde começar

- Quer rodar o projeto? Veja [Instalação e comandos](instalacao.md).
- Quer entender cada etapa? Veja [Pipeline](pipeline.md).
- Quer saber o que cada número significa? Veja [Indicadores](indicadores.md).

## Instalação e comandos

### Pré-requisitos

- Python 3.13.
- [uv](https://docs.astral.sh/uv/).
- Os quatro arquivos brutos do Inside Airbnb em `data/raw/`.

### Instalar as dependências

```bash
scripts/comandos_uv.sh sync
uv sync --all-groups
```

O segundo comando instala também os grupos `dev`, `dashboard` e `docs`.

### Comandos do projeto

Todos os comandos ficam em `scripts/comandos_uv.sh` (Linux) e
`scripts/comandos_uv.bat` (Windows). Sem argumento, o script mostra a lista.

| Comando | O que faz |
|---|---|
| `ingestao` | Grava as quatro tabelas `raw.*` no banco. |
| `staging` | Gera as quatro tabelas `staging.*`. |
| `marts` | Gera as nove tabelas `mart.*`, a partir de `data/mart/`. |
| `publicacao` | Exporta os marts para `data/publicacao/` (Parquet). |
| `dashboard` | Abre o painel no navegador (lendo o banco local). |
| `ui` | Abre o explorador do banco no navegador. |
| `test` | Roda os testes com cobertura. |
| `lint` | Verifica o estilo com ruff. |

A ordem de execução é: `ingestao`, `staging`, `marts`, e depois `publicacao`
e `dashboard`.

### Documentação

```bash
uv run mkdocs serve
```

Abre o site em `http://127.0.0.1:8000`.

## Pipeline

O pipeline tem quatro etapas. Cada uma lê só da etapa anterior e grava na sua.
A fronteira entre elas é deliberada: o que chegou (`raw`) fica separado do
que foi decidido (`staging`) e do que responde a uma pergunta (`mart`).

### 1. Ingestão (`raw`)

Lê `listings`, `calendar`, `reviews` e `neighbourhoods` e grava em `raw.*`.

- Tudo entra como texto. Não há conversão, descarte, deduplicação nem correção.
- Motivo: a fronteira entre o dado recebido e o dado decidido precisa existir
  em um lugar só, que é a passagem para `staging`.
- Se algum arquivo faltar, a ingestão para antes de gravar qualquer tabela.

### 2. Staging (`staging`)

Converte os tipos e valida os valores.

- Valor que não converte para o tipo alvo interrompe a execução, com a tabela,
  a coluna e um exemplo. Nunca vira nulo em silêncio.
- Linha inteira repetida sai, e a quantidade é contada.
- Chave repetida com conteúdo diferente interrompe a execução.
- Preço vira `DECIMAL(10,2)`, sem arredondamento: um valor com mais de duas
  casas decimais é recusado.
- Datas sem hora viram `DATE`.

### 3. Marts (`mart`)

Cada arquivo de `data/mart/` cria uma tabela. Os arquivos seguem o padrão
`XX_descricao.sql`, numerados a partir de 01.

- Cada arquivo tem uma única instrução `CREATE OR REPLACE TABLE`.
- As nove tabelas são criadas numa única transação. Se uma falhar, nenhuma é
  alterada.
- O Python não contém SQL de mart.

### 4. Publicação (`data/publicacao`)

Exporta os nove marts para arquivos Parquet e grava `atualizacao.json` com a
data de geração e a quantidade de linhas de cada tabela. Esses arquivos são o
que o painel publicado lê.



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

---

## Dados

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

### Fontes

Os quatro arquivos do Inside Airbnb para o Rio de Janeiro:

| Arquivo | Tabela no banco | Linhas |
|---|---|---|
| `listings` (anúncios) | `raw.anuncios` | 48.247 |
| `calendar` (calendário) | `raw.calendario` | 17.610.155 |
| `reviews` (avaliações) | `raw.avaliacoes` | 1.461.658 |
| `neighbourhoods` (bairros) | `raw.bairros` | 160 |

### Relações entre as tabelas

- Cada avaliação pertence a um anúncio (`avaliacoes.listing_id` referencia
  `anuncios.id`).
- Cada dia do calendário pertence a um anúncio (`calendario.listing_id`
  referencia `anuncios.id`).
- Cada anúncio está em um bairro (`anuncios.neighbourhood_cleansed` referencia
  `bairros.neighbourhood`).

### Tabelas do schema `mart`

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

## Indicadores

Cada indicador responde a uma pergunta. Os números abaixo são os da última
execução do pipeline.

### Ocupação

A ocupação é a parte dos dias do calendário em que o imóvel aparece como
indisponível. Ela conta reservas **e** bloqueios feitos pelo anfitrião, porque
o dado não separa os dois.

### Receita potencial

É o preço do anúncio multiplicado pelos dias ocupados no mês. O calendário não
traz o preço de cada dia, então o cálculo usa o preço do anúncio para o ano
inteiro. Por isso é uma **estimativa**.

### Sazonalidade

Mostra em quais meses do ano há mais avaliações. Como os anos não têm o mesmo
número de meses com dados, cada mês é a média dos anos em que existe. O ano de
2026 está incompleto e entra só nos meses já ocorridos.

### Correlação

O indicador de comodidades usa a correlação de Pearson (r), de -1 a 1. Um r perto
de 0 quer dizer que não há relação linear. Relação não é prova de causa.

### Perguntas respondidas

1. Qual o preço médio e mediano da diária por bairro?
2. Qual a taxa de ocupação estimada por bairro?
3. Qual a receita potencial mensal por anúncio?
4. Qual a fatia de anfitriões com mais de um imóvel? (23,9% dos anfitriões; 57,6%
   dos imóveis)
5. Como evolui o número de avaliações por mês, e há sazonalidade?
6. Quanto custa a mais um imóvel inteiro em relação a um quarto privado?
7. Superhosts têm notas e ocupação maiores?
8. Há relação entre o número de comodidades e o preço ou a nota?

## Dashboard

O painel tem duas páginas: **Anfitrião** e **Investidor**. Cada gráfico traz
um título, o gráfico e uma explicação curta logo abaixo.

### Rodar localmente

```bash
scripts/comandos_uv.sh dashboard
```

Com o banco `data/insideairbnb.duckdb` presente, o painel lê o banco.

### Origem dos dados

A origem é escolhida nesta ordem:

1. A variável de ambiente `DASHBOARD_ORIGEM` (`banco` ou `publicacao`), se definida.
2. O banco local, se o arquivo `data/insideairbnb.duckdb` existir.
3. Os arquivos Parquet de `data/publicacao/`, caso contrário.

O rodapé mostra a data em que os dados foram gerados.

### Publicação

O painel é publicado no Streamlit Community Cloud. A publicação lê os arquivos
Parquet de `data/publicacao/`, que precisam estar no repositório. O arquivo de
entrada é `src/dashboard/app.py`.
