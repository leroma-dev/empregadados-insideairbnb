# Marts: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar nove tabelas no schema `mart` a partir do staging, executando os arquivos SQL de `data/mart/` em ordem, numa única transação, com saída na tela e falha limpa.

**Architecture:** Um módulo `pipeline.marts` com funções pequenas: listagem e validação dos arquivos SQL, execução de cada arquivo, e `executar_todos` que valida tudo antes de criar qualquer tabela e grava numa transação. O Python não contém SQL de mart (regra M7); o SQL vive em `data/mart/`. `pipeline.db` e `pipeline.staging` são reaproveitados sem alteração.

**Tech Stack:** Python 3.13, uv, DuckDB 2.0.0 (já no `pyproject.toml`), pytest, pytest-cov, ruff.

**Spec:** `docs/spec/08_mart_spec.md` (status APROVADA). Este plano argumenta a partir dela; quem implementa lê as duas.

## Global Constraints

- Python 3.13; dependências gerenciadas com uv.
- Banco: `data/insideairbnb.duckdb`; leitura de `staging.*`; escrita apenas em `mart.*`. Nunca escrever em `raw` nem em `staging`.
- Cada arquivo de `data/mart/` tem exatamente uma instrução: `CREATE OR REPLACE TABLE mart.<nome> AS ...` (M7).
- Nome do arquivo: `XX_descricao_do_mart.sql`, com `XX` sequencial começando em 01, sem lacunas (M7).
- Cabeçalho de comentários em cada arquivo com a linha `-- Mart: mart.<nome>`, que deve bater com o nome do `CREATE` (spec, seção ARQUIVOS SQL).
- As nove tabelas são gravadas numa única transação; falha em qualquer uma não altera nenhuma (M2).
- `CREATE OR REPLACE TABLE`: rodar duas vezes dá o mesmo resultado (M1).
- Nenhum arquivo de mart escreve em `staging` ou `raw` (M3).
- Preço e nota nulos saem só das médias que dependem deles; a contagem mostra quantos ficaram de fora (M4).
- Conversão, validação e erro de tipo ficam no staging; mart não converte nada (sem `TRY_CAST`, `try_strptime` ou `try/except` em volta de SQL de negócio).
- `sys.stdout.reconfigure(encoding="utf-8")` no ponto de entrada.
- Testes em `tests/test_marts.py` usam `tmp_path`; nunca tocam em `data/mart/` nem no `.duckdb` real.
- Comandos uv são rodados pelo desenvolvedor via `scripts/comandos_uv.sh <comando>`. Nenhum comando roda automaticamente.
- Commits no git são feitos pelo desenvolvedor; o plano não tem etapa de commit.

## Review Focus

1. Arquivo com duas instruções SQL (ex.: dois `CREATE`) é recusado antes de qualquer criação. Pinned by Task 2.
2. Cabeçalho `-- Mart:` diferente do nome do `CREATE` é recusado, com o nome do arquivo na mensagem. Pinned by Task 2.
3. Lacuna ou fora de ordem na numeração (ex.: `01`, `03`) é recusada antes de executar. Pinned by Task 1.
4. Staging ausente: nenhuma tabela `mart` é criada, e a mensagem manda rodar `uv run python -m pipeline.staging`. Pinned by Task 5.
5. Mart com zero linhas é válido: aparece na saída com `0 linhas`, e não é erro. Pinned by Task 5.

---

### Task 1: Listagem e ordem dos arquivos

**Files:**
- Create: `src/pipeline/marts.py`
- Test: `tests/test_marts.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `PASTA_SQL: Path` = `data/mart` da raiz do projeto, calculado a partir de `__file__`.
  - `listar_arquivos(pasta: Path) -> list[Path]`: arquivos `*.sql` de `pasta` cujo nome bate com `^\d{2}_[a-z0-9_]+\.sql$`, ordenados pelo nome. Levanta `ErroArquivoMart` se a numeração não começar em 01 ou tiver lacuna ou repetição.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_lista_em_ordem_e_ignora_o_que_nao_e_arquivo_de_mart(tmp_path):
    (tmp_path / "02_b.sql").write_text("", encoding="utf-8")
    (tmp_path / "01_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "notas.txt").write_text("", encoding="utf-8")
    nomes = [p.name for p in marts.listar_arquivos(tmp_path)]
    assert nomes == ["01_a.sql", "02_b.sql"]


def test_lacuna_na_numeracao_para_antes_de_executar(tmp_path):
    (tmp_path / "01_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "03_c.sql").write_text("", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart):
        marts.listar_arquivos(tmp_path)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/comandos_uv.sh test`
Expected: FAIL, `marts` sem `listar_arquivos`.

- [ ] **Step 3: Criar `src/pipeline/marts.py`**

Docstring no topo com a spec resumida e o motivo de cada regra (M1 a M7). Definir `PASTA_SQL`, a classe `ErroArquivoMart(Exception)` com os atributos da Task 2 (`arquivo`, `motivo`) e `listar_arquivos`. A numeração esperada é 01, 02, ..., n, sem lacuna.

- [ ] **Step 4: Rodar e ver passar**

Expected: os dois testes PASS.

---

### Task 2: Validação de cada arquivo

**Files:**
- Modify: `src/pipeline/marts.py`
- Test: `tests/test_marts.py`

**Interfaces:**
- Consumes: `ErroArquivoMart` e `listar_arquivos` (Task 1).
- Produces:
  - `class ErroArquivoMart(Exception)`: atributos `arquivo: str`, `motivo: str`. A mensagem é `f"{arquivo}: {motivo}"`.
  - `nome_mart(caminho: Path) -> str`: lê a linha `-- Mart: mart.<nome>` do cabeçalho e devolve `mart.<nome>`. Sem cabeçalho, levanta `ErroArquivoMart`.
  - `verificar_arquivo(con, caminho: Path) -> str`: confere que o texto tem exatamente uma instrução (`duckdb.extract_statements`), que ela é `CREATE OR REPLACE TABLE <nome> AS`, e que `<nome>` é igual ao de `nome_mart`. Devolve `<nome>`. Não executa nada.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_arquivo_valido_devolve_o_nome_da_tabela(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text("-- Mart: mart.teste\n\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\n", encoding="utf-8")
    assert marts.verificar_arquivo(None, arq) == "mart.teste"


def test_duas_instrucoes_sao_recusadas(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text("-- Mart: mart.teste\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\nSELECT 2;\n", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart) as e:
        marts.verificar_arquivo(None, arq)
    assert "01_teste.sql" in str(e.value)


def test_cabecalho_diferente_do_create_e_recusado(tmp_path):
    arq = tmp_path / "01_teste.sql"
    arq.write_text("-- Mart: mart.outro\nCREATE OR REPLACE TABLE mart.teste AS SELECT 1 AS x;\n", encoding="utf-8")
    with pytest.raises(marts.ErroArquivoMart):
        marts.verificar_arquivo(None, arq)
```

`verificar_arquivo` não usa `con`; o parâmetro fica por consistência com `executar`. O teste passa `None`.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `ErroArquivoMart` e `verificar_arquivo` não definidos.

- [ ] **Step 3: Implementar**

Usar `duckdb.extract_statements(texto)` para contar instruções. O nome do `CREATE` vem de uma expressão regular sobre o texto da única instrução; não concatenar nome vindo de fora em SQL.

- [ ] **Step 4: Rodar e ver passar**

Expected: os quatro testes de Task 1 e Task 2 PASS.

---

### Task 3: Execução de um arquivo

**Files:**
- Modify: `src/pipeline/marts.py`
- Test: `tests/test_marts.py`

**Interfaces:**
- Consumes: `verificar_arquivo` (Task 2).
- Produces: `executar(con, caminho: Path) -> tuple[str, int]`: executa o arquivo (a instrução única) e devolve `(nome_da_tabela, linhas)`, com `linhas` vindo de `SELECT count(*) FROM <nome>` na mesma conexão. Não abre transação; a transação é da Task 4.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_executar_cria_a_tabela_e_conta_no_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    arq = tmp_path / "01_teste.sql"
    arq.write_text("-- Mart: mart.teste\nCREATE OR REPLACE TABLE mart.teste AS SELECT * FROM (VALUES (1), (2), (3)) t(x);\n", encoding="utf-8")
    assert marts.executar(con, arq) == ("mart.teste", 3)
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `executar` não definido.

- [ ] **Step 3: Implementar**

`verificar_arquivo` antes de executar; depois o texto do arquivo como uma instrução única; contagem por `count(*)`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 4: Todas as nove tabelas numa transação

**Files:**
- Modify: `src/pipeline/marts.py`
- Test: `tests/test_marts.py`

**Interfaces:**
- Consumes: `listar_arquivos`, `verificar_arquivo`, `executar` (Tasks 1 a 3).
- Produces: `executar_todos(con, pasta: Path = PASTA_SQL) -> list[tuple[str, int]]`: valida todos os arquivos (`verificar_arquivo`) antes de criar qualquer tabela; depois, numa única transação (`con.begin()`, `con.commit()`, e `con.rollback()` seguido de `raise` no erro, como em `staging.transformar`), executa os arquivos na ordem e devolve `(tabela, linhas)` de cada um. Cria o schema com `CREATE SCHEMA IF NOT EXISTS mart` dentro da transação.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_todos_os_arquivos_geram_as_tabelas(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)  # helper: staging.anuncios etc. com uma linha
    pasta = _pasta_com_tres_marts_validos(tmp_path)          # helper: 01..03 com SELECTs simples
    resultado = marts.executar_todos(con, pasta)
    assert [t for t, _ in resultado] == ["mart.t1", "mart.t2", "mart.t3"]


def test_falha_no_terceiro_arquivo_nao_cria_nenhuma(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path, quebrado="03_t3.sql")  # SQL com erro de referência
    with pytest.raises(Exception):
        marts.executar_todos(con, pasta)
    tabelas = con.execute("select table_name from information_schema.tables where table_schema='mart'").fetchall()
    assert tabelas == []


def test_duas_execucoes_dao_o_mesmo_resultado(tmp_path, monkeypatch):
    con = _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path)
    primeira = marts.executar_todos(con, pasta)
    assert marts.executar_todos(con, pasta) == primeira
```

Os helpers `_banco_com_staging_minimo` e `_pasta_com_tres_marts_validos` são escritos no arquivo de teste.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

Validação de todos os arquivos antes do `con.begin()`. Erro de execução dentro da transação: rollback e `raise`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 5: Saída na tela, staging ausente e ponto de entrada

**Files:**
- Modify: `src/pipeline/marts.py`
- Test: `tests/test_marts.py`

**Interfaces:**
- Consumes: `executar_todos`, `ErroArquivoMart` (Task 4); `conectar` de `pipeline.db`; `formatar_contagem` de `pipeline.ingestao` (reuso).
- Produces:
  - `faltantes_staging(con) -> list[str]`: nomes de `staging.anuncios`, `staging.calendario`, `staging.avaliacoes`, `staging.bairros` que não existem.
  - `main(conectar_fn=conectar, pasta: Path = PASTA_SQL) -> int`.
  - Saída: uma linha por mart, `f"{tabela:<26} {formatar_contagem(n)} linhas"`; última linha `total` com a soma.
  - Staging faltando: lista as tabelas, diz para rodar `uv run python -m pipeline.staging`, devolve 1, sem criar tabela `mart`.
  - `ErroArquivoMart` ou erro do DuckDB: imprime a mensagem, devolve 1.
  - `if __name__ == "__main__": sys.exit(main())`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_saida_uma_linha_por_mart_e_total(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _banco_com_staging_minimo(tmp_path, monkeypatch)  # helper; reabre o mesmo arquivo
    assert marts.main(pasta=_pasta_com_tres_marts_validos(tmp_path)) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert linhas[-1].startswith("total")
    assert sum(1 for ln in linhas if ln.startswith("mart.")) == 3


def test_staging_faltando_manda_rodar_a_etapa_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    assert marts.main(pasta=_pasta_com_tres_marts_validos(tmp_path)) == 1
    assert "pipeline.staging" in capsys.readouterr().out


def test_mart_com_zero_linhas_e_valido(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _banco_com_staging_minimo(tmp_path, monkeypatch)
    pasta = _pasta_com_tres_marts_validos(tmp_path, vazio="02_t2.sql")  # WHERE 1 = 0
    assert marts.main(pasta=pasta) == 0
    assert "mart.t2" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

`faltantes_staging` antes de qualquer `CREATE`. `main` chama `conectar_fn()`, checa `faltantes_staging` no mesmo connection; se faltar, encerra com 1 sem criar `mart` (regra R9 da etapa 2: pode criar um `.duckdb` vazio, mas nenhuma tabela `mart`). `sys.stdout.reconfigure(encoding="utf-8")` no início de `main`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 6: Comando no script do uv

**Files:**
- Modify: `scripts/comandos_uv.sh`
- Modify: `scripts/comandos_uv.bat`

**Interfaces:**
- Consumes: `main` da Task 5.
- Produces: comando `marts` (`uv run python -m pipeline.marts`), listado na ajuda.

- [ ] **Step 1: Acrescentar o comando nos dois scripts**

Em `comandos_uv.sh`: linha de ajuda `marts` e `marts)` no `case`, com `uv run python -m pipeline.marts`, logo depois de `staging`. Em `comandos_uv.bat`: o equivalente, no padrão de `staging`.

- [ ] **Step 2: Verificar a ajuda**

Run: `scripts/comandos_uv.sh`
Expected: lista inclui `marts`, e nenhum uv é executado.

---

### Task 7: Execução real e critérios de aceite

**Files:** nenhum.

**Interfaces:**
- Consumes: `scripts/comandos_uv.sh marts` (Task 6), com o staging da etapa 2 já criado.
- Produces: nada; é conferência contra a spec.

- [ ] **Step 1: Pré-condição**

Expected: `staging` com as quatro tabelas da etapa 2. Nenhum outro processo com o `.duckdb` aberto (ver o lock do MCP na etapa 2).

- [ ] **Step 2: Executar**

Run: `scripts/comandos_uv.sh marts`
Expected: nove linhas `mart.<tabela>` e linha `total`; código de saída 0. Contagens de referência:
- `mart.preco_bairro` 156 linhas.
- `mart.ocupacao_bairro` 156 linhas.
- `mart.receita_mensal_anuncio` 573.911 linhas.
- `mart.multi_host` 1 linha.
- `mart.reviews_mensal` 196 linhas.
- `mart.inteiro_vs_privado` 2 linhas.
- `mart.superhost` 2 linhas.
- `mart.amenities` 1 linha.
- `mart.sazonalidade_reviews` 12 linhas.

- [ ] **Step 3: Reexecutar**

Expected: saída idêntica à anterior (MA10).

- [ ] **Step 4: Conferir os critérios da spec**

Consultar as tabelas `mart.*` em modo somente leitura e comparar com MA1 a MA11:
- MA2: soma de `anuncios_com_preco` em `mart.preco_bairro` = 44.147.
- MA3: 156 bairros em `mart.ocupacao_bairro`; `taxa_ocupacao_pct` entre 0 e 100.
- MA4: soma de `dias_ocupados` em `mart.receita_mensal_anuncio` = 6.843.609.
- MA5: `mart.multi_host`: `anfitrioes` = 26.869; `multi_host` = 6.411.
- MA6: soma de `reviews` em `mart.reviews_mensal` = 1.461.658.
- MA7: 36.148 + 7.455 = 43.603 em `mart.inteiro_vs_privado`.
- MA8: soma de `anuncios` em `mart.superhost` = 48.247.
- MA9: `anuncios` em `mart.amenities` = 48.247.
- MA11: uma falha forçada (Task 4) deixa `mart` sem tabelas.

Expected: todos batem. Divergência vira correção antes de dar a etapa como concluída.

## Checklist de aceite (plano)

- [ ] Task 1 a Task 5: testes de `tests/test_marts.py` PASS.
- [ ] Cobertura de `src/pipeline/marts.py` reportada por `scripts/comandos_uv.sh test`.
- [ ] Task 6: `marts` aparece na ajuda dos dois scripts.
- [ ] Task 7: execução real bate com as contagens de referência; MA1 a MA11 conferidos.
- [ ] Docstring do `marts.py` tem o motivo de cada regra (M1 a M7).
