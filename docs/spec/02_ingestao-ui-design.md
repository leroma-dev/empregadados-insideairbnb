# Design: ingestão raw e explorador do banco (insideairbnb)

Data: 2026-11-05
Status: aprovado (design geral). Nesta etapa só a spec é entregue: os arquivos
de `src/` contêm apenas a docstring com a spec, sem código.

## Intenção

O projeto transforma os dados públicos do Inside Airbnb (Rio de Janeiro) em
indicadores. Esta etapa cria a **camada raw**: os quatro arquivos baixados
entram no DuckDB exatamente como chegaram, em tabelas com nomes em português.
Também cria uma ferramenta para explorar o banco pelo navegador.

O motivo central: a fronteira entre "o dado que chegou" e "o dado que eu
decidi" precisa existir em um lugar só. Esse lugar é a passagem de raw para
staging (etapa 2). Se alguma correção acontecer na ingestão, a fronteira some.

## Objetivos

- Ingerir os quatro arquivos de `data/raw/` em `data/insideairbnb.duckdb`, no
  schema `raw`, sem nenhuma transformação.
- Rodar a ingestão quantas vezes for preciso com o mesmo resultado.
- Falhar alto e antes de gravar, se algum arquivo estiver faltando.
- Oferecer um explorador do banco no navegador (`ui.py`), sem criar banco.

## Não-objetivos

- Limpeza, tipagem, deduplicação, filtros ou regras de negócio (etapa 2).
- Dashboard Streamlit e documentação MkDocs (outras etapas).
- Baixar dados. O download continua em `scripts/download_data.py`.

## Antiobjetivos

- Um banco vazio ou parcial que pareça ingestão concluída.
- Um explorador que crie o arquivo `.duckdb` quando ele não existe.
- A ingestão depender de servidor, navegador ou da extensão `ui`.

## Restrições

- Python 3.13, dependências com uv, DuckDB como banco.
- Código fonte em `src/`, com subpastas. Testes em `tests/`. Dados em `data/`
  (raw, staging, mart). Ferramentas de desenvolvimento: ruff e pytest com coverage.
- Saída de terminal em utf-8 (o usuário roda no Prompt de Comando do Windows e no bash do linux).
- O arquivo `.duckdb` aceita um único processo escrevendo.

## Abordagens consideradas

**A. pandas com `dtype=str` (escolhida).** `pandas.read_csv` lê cada
arquivo como texto e o DataFrame vai para o DuckDB. Segue a spec ao pé da
letra e é fácil de testar. Trade-off: `reviews.csv.gz` tem 162 MB comprimido;
carregar tudo como texto em memória pode ser pesado. Aceito porque é uma
execução pontual e local.

**B. DuckDB lendo direto com `read_csv(..., all_varchar=true)`.** Não passa
por pandas e faz streaming. Trade-off: "campo vazio vira nulo" e "não
interpretar NA como nulo" precisam ser configurados explicitamente no DuckDB,
e a spec ficaria menos literal ("dtype=str").

Escolhi A por ser o que a spec descreve. Se a memória for um problema na
execução real, B é a alternativa, e o resultado observável não muda.

## Desenho

### Estrutura

```
src/
  pipeline/
    db.py          conectar(), gravar(); caminho do banco fixo na pasta data
    ingestao.py   ingestão raw; ponto de entrada da etapa
  ui/
    ui.py          explorador do banco pelo navegador
tests/
  test_db.py
  test_ingestao.py
  test_ui.py
scripts/
  comandos_uv.bat  comandos do uv, um por argumento (ver abaixo)
data/
  raw/             os quatro arquivos
  insideairbnb.duckdb   gerado (fora do git)
```

### Script de comandos uv

Arquivo `scripts/comandos_uv.bat`, para o Prompt de Comando do Windows.

- Sem argumento: imprime a lista de comandos e não executa nada.
- Com um argumento (ex.: `scripts\comandos_uv.bat test`): executa somente o
  comando uv correspondente, uma vez.
- Nunca executa uv por conta própria, nem ao ser aberto ou importado.

Comandos previstos: `init`, `add-deps`, `sync`, `lint`, `format`, `test`.
Um `.sh` equivalente para o bash do Linux pode ser adicionado depois.

### Mapa arquivo → tabela (schema `raw`)

| Arquivo em `data/raw/` | Tabela |
|---|---|
| `listings.csv.gz` | `raw.anuncios` |
| `calendar.csv.gz` | `raw.calendario` |
| `reviews.csv.gz` | `raw.avaliacoes` |
| `neighbourhoods.csv` | `raw.bairros` |

### Módulo `db` (primeiro artefato)

- `conectar()` abre `data/insideairbnb.duckdb`. O caminho é calculado a partir
  da localização do próprio arquivo `db.py`, nunca da pasta corrente.
  Cria o arquivo se faltar, e cria o schema `raw` se faltar.
- Importar `db` não abre banco nem cria arquivo.
- `gravar(nome_qualificado, df)` faz `CREATE OR REPLACE TABLE` e devolve a
  contagem de linhas **consultada no banco**, não o `len(df)`.

### Ingestão (segundo artefato)

1. Verifica os quatro arquivos em `data/raw/` antes de abrir o banco. Faltando
   algum: lista os que faltam, mostra a pasta onde procurou, `sys.exit(1)`.
2. Lê cada arquivo com `encoding="utf-8"`, `dtype=str`, `keep_default_na=False`
   e `na_values=[""]`. Os `.csv.gz` são lidos direto pelo pandas.
   Campo vazio vira nulo; `"NA"`, `"null"`, `"N/A"` continuam texto.
3. Grava cada DataFrame com `gravar()`.
4. Imprime uma linha por tabela (nome qualificado e contagem vinda do banco,
   milhar com ponto) e uma linha final com o total.
5. Reconfigura stdout para utf-8 no início.
6. Termina e devolve o terminal.

Sem conversão, renomeação, descarte, deduplicação ou correção de valor.

### Explorador (terceiro artefato)

1. Verifica se `data/insideairbnb.duckdb` existe. Se não existir: diz que é
   preciso rodar a ingestão antes, `sys.exit(1)`, sem criar arquivo.
2. Abre o banco, executa `INSTALL ui; LOAD ui;` e `CALL start_ui()`, que sobe
   `http://localhost:4213` e abre o navegador.
3. Mantém o processo vivo, imprime a URL e "Ctrl+C para encerrar".
4. No Ctrl+C: fecha a conexão e sai sem traceback.
5. Não importa `ingestao`, e `ingestao` não importa `ui`.
6. stdout em utf-8.

## Critérios de aceite

Módulo `db`:
- Importar `pipeline.db` não cria arquivo nem abre banco.
- `conectar()` chamado de outra pasta cria `data/insideairbnb.duckdb` dentro
  do projeto, não na pasta corrente.
- `gravar()` com DataFrame de 3 linhas devolve 3; rodar de novo continua devolvendo 3.

Ingestão:
- Imprime quatro linhas (uma por tabela) e o total de registros.
- Duas execuções seguidas imprimem exatamente o mesmo.
- `SELECT * FROM raw.anuncios` devolve todas as colunas como VARCHAR.
- Remover um dos quatro arquivos faz o script parar antes de gravar qualquer tabela.
- O processo termina sozinho.

Explorador:
- `uv run python src/ui/ui.py` abre o navegador em `localhost:4213` com o schema
  `raw` e as quatro tabelas.
- Ctrl+C devolve o terminal sem traceback; a ingestão roda logo depois sem erro de lock.
- Com o `.duckdb` renomeado, o explorador para com mensagem e não cria arquivo.

## O que fica para o construtor

- Detalhes de teste (fixtures, arquivos pequenos de exemplo).
- Formato exato das mensagens de erro, desde que cumpram o que está acima.

## Decisões minhas (não estavam na spec; as de 1 a 8 foram aprovadas e ficam mantidas)

1. Código em `src/pipeline/` e `src/ui/`. A spec citava `ui.py` na raiz; a
   regra de usar `src/` prevaleceu.
2. Tabelas: `anuncios`, `calendario`, `avaliacoes`, `bairros` (nomes em
   português, como pedido). Os nomes são proposta.
3. Escrita atômica: toda a ingestão roda em uma transação. Se falhar no meio,
   o banco fica no estado anterior, não parcial.
4. `keep_default_na=False` e `na_values=[""]`: sem isso, o pandas converteria
   silenciosamente `"NA"`, `"null"` e `"N/A"` em nulo, o que viola a regra de
   não corrigir valores.
5. O `README.md` diz que os dados "foram transformados". Isso contradiz a
   ingestão raw; proponho corrigir o texto em outra etapa.
6. `data/insideairbnb.duckdb` entra no `.gitignore`.
7. O explorador abre o banco em modo normal (não somente leitura), porque a
   extensão `ui` precisa de conexão viva. A exclusão com a ingestão é a da spec.
8. Não há spec fornecida para o módulo `db` além dos critérios de aceite.
   Deduzi `conectar()` e `gravar()` a partir deles.
