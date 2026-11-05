# Spec geral: passos do projeto insideairbnb

Escrito para: quem vai construir e conferir o projeto, incluindo o próprio
desenvolvedor daqui a algumas semanas.

Esta spec resume a ordem dos passos. O detalhe de cada artefato está nas
docstrings dos arquivos em `src/` e no design em
`docs/spec/02_ingestao-ui-design.md`.

## Stack

- Python 3.13, dependências gerenciadas com uv.
- DuckDB como banco (`data/insideairbnb.duckdb`).
- Streamlit para apresentação (etapa futura).
- MkDocs para documentação, publicada no GitHub Pages (etapa futura).
- ruff para lint e formatação; pytest com coverage para testes.

## Estrutura de pastas

```
src/        código fonte, com subpastas (pipeline/, ui/)
tests/      testes unitários
scripts/    comandos auxiliares (comandos_uv.bat) e download de dados
data/raw/       dados brutos, sem alteração (fora do git)
data/staging/   dados limpos e tipados (etapa 2)
data/mart/      tabelas analíticas e indicadores (etapa 3)
docs/spec/      specs gerais e design aprovado da etapa de ingestão
```

## Passos

### Passo 0: ambiente uv

Comandos em `scripts/comandos_uv.bat`. Cada comando é executado manualmente,
um por vez, pelo desenvolvedor. Nada roda automaticamente.

1. `scripts\comandos_uv.bat init`: cria o `pyproject.toml` com Python 3.13.
2. `scripts\comandos_uv.bat add-deps`: adiciona duckdb e pandas, e ruff,
   pytest e pytest-cov no grupo dev.
3. `scripts\comandos_uv.bat sync`: instala as dependências.

Pronto quando: `sync` termina sem erro.

### Passo 1: estrutura e git

- Adicionar `data/insideairbnb.duckdb` ao `.gitignore`.
- Confirmar que `data/raw/` contém os quatro arquivos: `listings.csv.gz`,
  `calendar.csv.gz`, `reviews.csv.gz`, `neighbourhoods.csv`.

Pronto quando: o arquivo do banco aparece como ignorado no `git status`.

### Passo 2: módulo de banco (`src/pipeline/db.py`)

Conexão com caminho fixo na pasta do projeto, criação do schema `raw` e
`gravar()` com contagem consultada no banco.

Pronto quando: os três critérios de aceite de `db.py` passam (ver a docstring).

### Passo 3: ingestão raw (`src/pipeline/ingestao.py`)

Verifica os quatro arquivos, lê tudo como texto e grava as quatro tabelas
em `raw`, numa única transação, sem nenhuma transformação.

Pronto quando: a execução imprime quatro linhas e o total, roda igual duas
vezes e para antes de gravar se faltar um arquivo.

### Passo 4: testes da etapa 1

Testes unitários em `tests/` para `db.py` e `ingestao.py`. Arquivos de
exemplo pequenos, para não depender dos arquivos grandes de `data/raw/`.

Rodar: `scripts\comandos_uv.bat test`.

Pronto quando: os testes passam e a cobertura é mostrada no terminal.

### Passo 5: explorador (`src/ui/ui.py`)

Sobe o servidor da extensão `ui` do DuckDB, mantém o processo de pé até
Ctrl+C e não cria banco.

Pronto quando: os três critérios de aceite de `ui.py` passam (ver a docstring).

### Passo 6: testes do explorador e lint

- Testes em `tests/` para o caminho de erro do `ui.py` (banco ausente), sem
  subir o servidor.
- `scripts\comandos_uv.bat lint` e `scripts\comandos_uv.bat format` sem erros.

### Passo 7 (futuro): staging, etapa 2

Passagem de raw para staging: tipagem, limpeza e cada decisão registrada.
Fora do escopo desta spec.

### Passo 8 (futuro): mart, Streamlit e MkDocs

Indicadores em `data/mart/`, apresentação em Streamlit, documentação em
MkDocs publicada no GitHub Pages. Fora do escopo desta spec.

## Fora do escopo desta spec

- Qualquer código além da ingestão, do módulo de banco e do explorador.
- Correção do `README.md` (ver decisão 5 do design).
