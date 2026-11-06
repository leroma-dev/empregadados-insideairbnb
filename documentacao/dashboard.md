# Dashboard

O painel tem duas páginas: **Anfitrião** e **Investidor**. Cada gráfico traz
um título, o gráfico e uma explicação curta logo abaixo.

## Rodar localmente

```bash
scripts/comandos_uv.sh dashboard
```

Com o banco `data/insideairbnb.duckdb` presente, o painel lê o banco.

## Origem dos dados

A origem é escolhida nesta ordem:

1. A variável de ambiente `DASHBOARD_ORIGEM` (`banco` ou `publicacao`), se definida.
2. O banco local, se o arquivo `data/insideairbnb.duckdb` existir.
3. Os arquivos Parquet de `data/publicacao/`, caso contrário.

O rodapé mostra a data em que os dados foram gerados.

## Publicação

O painel é publicado no Streamlit Community Cloud. A publicação lê os arquivos
Parquet de `data/publicacao/`, que precisam estar no repositório. O arquivo de
entrada é `src/dashboard/app.py`.
