# Instalação e comandos

## Pré-requisitos

- Python 3.13.
- [uv](https://docs.astral.sh/uv/).
- Os quatro arquivos brutos do Inside Airbnb em `data/raw/`.

## Instalar as dependências

```bash
scripts/comandos_uv.sh sync
uv sync --all-groups
```

O segundo comando instala também os grupos `dev`, `dashboard` e `docs`.

## Comandos do projeto

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

## Documentação

```bash
uv run mkdocs serve
```

Abre o site em `http://127.0.0.1:8000`.
