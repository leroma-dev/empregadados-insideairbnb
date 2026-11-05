# Ingestão raw e explorador do banco Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingerir os quatro arquivos de `data/raw/` no schema `raw` do DuckDB, sem nenhuma transformação, e oferecer um explorador do banco pelo navegador que nunca cria arquivo.

**Architecture:** Pacote instalável com dois pacotes de código (`pipeline` com o módulo de banco e a ingestão; `ui` com o explorador). `pipeline.db` concentra caminho e conexão; `pipeline.ingestao` lê tudo como texto e grava numa única transação; `ui.ui` só abre o banco existente e sobe o servidor da extensão.

**Tech Stack:** Python 3.13, uv, DuckDB, pandas, pytest, pytest-cov, ruff, hatchling.

**Spec:** `docs/spec/02_ingestao-ui-design.md` (design aprovado) e as docstrings de `src/pipeline/db.py`, `src/pipeline/ingestao.py` e `src/ui/ui.py`. Este plano argumenta a partir delas; quem implementa lê as três.

## Global Constraints

- Python 3.13; dependências gerenciadas com uv.
- Pré-requisito: o `.venv` do projeto existe e está em uso em toda execução (ver seção abaixo).
- Banco: `data/insideairbnb.duckdb`, schema `raw`, tabelas `raw.anuncios`, `raw.calendario`, `raw.avaliacoes`, `raw.bairros`.
- Leitura com `encoding="utf-8"`, `dtype=str`, `keep_default_na=False`, `na_values=[""]`. Nenhuma conversão de tipo, linha descartada, deduplicação ou valor corrigido.
- Escrita da ingestão em uma única transação; falha no meio deixa o banco como estava.
- `sys.stdout.reconfigure(encoding="utf-8")` em todo ponto de entrada.
- Código em `src/` com subpastas; testes em `tests/`; dados em `data/`.
- Comandos uv são rodados pelo desenvolvedor, um por vez, via `scripts\comandos_uv.bat <comando>` (Windows) ou `scripts/comandos_uv.sh <comando>` (Linux). Nenhum comando uv roda automaticamente.
- Testes unitários usam `tmp_path` e nunca tocam em `data/raw/` ou no `.duckdb` real.
- Commits no git são feitos somente pelo desenvolvedor; o plano não tem etapa de commit no git. Commits no banco (transações DuckDB) fazem parte da ingestão, como descrito nas tarefas 4 e 7.

## Pré-requisito: `.venv`

- O `.venv` na raiz do projeto deve existir antes de qualquer tarefa. Ele é criado por `scripts\comandos_uv.bat sync` (Windows) ou `scripts/comandos_uv.sh sync` (Linux).
- O `.venv` deve estar ativo em toda execução de Python, inclusive quando o agente (Claude) roda comandos.
- Ativação por plataforma:
  - Linux/bash: `source .venv/bin/activate`
  - Prompt de Comando: `.venv\Scripts\activate.bat`
  - PowerShell: `.venv\Scripts\Activate.ps1`
- O estado do shell não persiste entre comandos do agente. Por isso, cada comando Python do agente roda com a ativação na mesma linha, por exemplo `source .venv/bin/activate && python -m pytest`, ou com `uv run`, que usa o `.venv` automaticamente.
- Se o `.venv` não existir, a tarefa para e o desenvolvedor roda `sync` antes de continuar.

## Review Focus

1. CEP e códigos com zero à esquerda (`"01310-100"`, `"01000000"`) permanecem texto na leitura e no banco. Pinned by Task 5 e Task 4.
2. Textos que o pandas trata como nulo por padrão (`"NA"`, `"null"`, `"N/A"`, `"NaN"`) permanecem texto. Pinned by Task 5.
3. Campo vazio vira NULL no banco, nunca string vazia; campo com aspas vazias (`""`) também vira NULL. Pinned by Task 5.
4. Texto com acento UTF-8 e campo com vírgula entre aspas (`"São Conrado"`, `"Rua A, 10"`) são lidos sem corrupção. Pinned by Task 5.
5. Banco aberto por outro processo (o explorador rodando) faz a ingestão falhar com mensagem clara, código 1, e sem alterar tabelas. Pinned by Task 7.

---

### Task 1: Pacote instalável e configuração de ferramentas

**Files:**
- Modify: `pyproject.toml`
- Create: `src/pipeline/__init__.py` (vazio)
- Create: `src/ui/__init__.py` (vazio)

**Interfaces:**
- Consumes: nada.
- Produces: pacotes importáveis `pipeline` e `ui` de qualquer pasta, após `uv sync`.

- [ ] **Step 1: Configurar o pyproject**

Em `[project]`: `requires-python = ">=3.13"`. Acrescentar:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipeline", "src/ui"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- [ ] **Step 2: Criar os `__init__.py` vazios**

- [ ] **Step 3: Instalar dependências**

Run (desenvolvedor): `scripts\comandos_uv.bat add-deps` e depois `scripts\comandos_uv.bat sync`
Expected: `sync` termina sem erro; `pyproject.toml` lista duckdb e pandas, e ruff, pytest e pytest-cov no grupo dev.

- [ ] **Step 4: Verificar importação de qualquer pasta**

Run (desenvolvedor), a partir de `C:\`: `uv run --project <raiz> python -c "import pipeline, ui; print('ok')"`
Expected: imprime `ok`.


---

### Task 2: Ignorar o banco no git

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nada.
- Produces: `data/insideairbnb.duckdb` e `data/insideairbnb.duckdb.wal` fora do git.

- [ ] **Step 1: Acrescentar as duas linhas**

```
data/insideairbnb.duckdb
data/insideairbnb.duckdb.wal
```

- [ ] **Step 2: Verificar**

Expected: após criar o arquivo (Task 4 ou 8), `git status` não o lista.


---

### Task 3: Caminho do banco e importação sem efeito colateral

**Files:**
- Create: `tests/test_db.py`
- Modify: `src/pipeline/db.py`

**Interfaces:**
- Consumes: nada.
- Produces: `caminho_banco() -> Path` (a pasta `data` do projeto, independente da pasta corrente).

- [ ] **Step 1: Escrever os testes que falham**

```python
import subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

def test_caminho_banco_independe_da_pasta(tmp_path):
    saida = subprocess.run(
        [sys.executable, "-c", "from pipeline.db import caminho_banco; print(caminho_banco())"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert Path(saida) == RAIZ / "data" / "insideairbnb.duckdb"

def test_importar_nao_cria_banco(tmp_path):
    alvo = RAIZ / "data" / "insideairbnb.duckdb"
    antes = alvo.exists()
    subprocess.run([sys.executable, "-c", "import pipeline.db"], cwd=tmp_path, check=True)
    assert alvo.exists() == antes
```

- [ ] **Step 2: Rodar e ver falhar**

Run (desenvolvedor): `scripts\comandos_uv.bat test`
Expected: FAIL, `caminho_banco` não definido.

- [ ] **Step 3: Implementar `caminho_banco() -> Path`**

Em `src/pipeline/db.py`, usar `Path(__file__).resolve().parents[2] / "data" / "insideairbnb.duckdb"`. Sem efeito colateral na importação.

- [ ] **Step 4: Rodar e ver passar**

Expected: os dois testes PASS.


---

### Task 4: Conexão e gravação

**Files:**
- Modify: `tests/test_db.py`
- Modify: `src/pipeline/db.py`

**Interfaces:**
- Consumes: `caminho_banco() -> Path` (Task 3).
- Produces:
  - `conectar() -> duckdb.DuckDBPyConnection`: cria a pasta `data` e o arquivo se faltarem, e cria o schema `raw`.
  - `gravar(con: duckdb.DuckDBPyConnection, nome_qualificado: str, df: pd.DataFrame) -> int`: `CREATE OR REPLACE TABLE` a partir do DataFrame e devolve `count(*)` consultado no banco, na mesma conexão.

Decisão: `gravar` recebe a conexão (ver `docs/spec/04` anterior, decisão 2); assim a ingestão roda numa transação só.

- [ ] **Step 1: Escrever os testes que falham**

Usar `monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")` em cada teste.

```python
def test_conectar_cria_arquivo_e_schema_raw(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    schemas = [r[0] for r in con.execute("select schema_name from information_schema.schemata").fetchall()]
    con.close()
    assert (tmp_path / "t.duckdb").exists()
    assert "raw" in schemas

def test_gravar_devolve_contagem_do_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    df = pd.DataFrame({"a": ["1", "2", "3"]})
    assert db.gravar(con, "raw.teste", df) == 3
    assert db.gravar(con, "raw.teste", df) == 3   # rodar de novo não acumula
    con.close()

def test_gravar_preserva_cep_com_zero_e_nulo(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    con = db.conectar()
    df = pd.DataFrame({"cep": ["01310-100", None], "na": ["NA", "x"]})
    db.gravar(con, "raw.teste", df)
    assert con.execute("select cep from raw.teste order by na").fetchall() == [("01310-100",), (None,)]
    assert con.execute("select na from raw.teste order by na").fetchall() == [("NA",), ("x",)]
    con.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `conectar` e `gravar` não definidos.

- [ ] **Step 3: Implementar `conectar()` e `gravar()`**

Assinaturas acima. Usar `CREATE SCHEMA IF NOT EXISTS raw` em `conectar`. Em `gravar`, registrar o DataFrame, `CREATE OR REPLACE TABLE {nome} AS SELECT * FROM _df`, desregistrar, consultar `count(*)`. `nome_qualificado` vem só de constantes internas.

- [ ] **Step 4: Rodar e ver passar**

Expected: os três testes PASS.


---

### Task 5: Leitura dos arquivos como texto

**Files:**
- Create: `tests/test_ingestao.py`
- Modify: `src/pipeline/ingestao.py`

**Interfaces:**
- Consumes: nada do projeto.
- Produces:
  - `MAPA: dict[str, str]` com exatamente:
    `{"listings.csv.gz": "raw.anuncios", "calendar.csv.gz": "raw.calendario", "reviews.csv.gz": "raw.avaliacoes", "neighbourhoods.csv": "raw.bairros"}`
  - `ler_arquivo(caminho: Path) -> pd.DataFrame`: lê com as opções fixas da spec; `.gz` é lido direto.

Os testes desta tarefa cobrem os itens 1 a 4 da Review Focus.

- [ ] **Step 1: Escrever os testes que falham**

Criar arquivos em `tmp_path` com `gzip.open(..., "wt", encoding="utf-8")`.

```python
def test_cep_com_zero_fica_texto(tmp_path):
    p = tmp_path / "a.csv.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write("cep\n01310-100\n")
    assert ingestao.ler_arquivo(p)["cep"].tolist() == ["01310-100"]

def test_textos_que_pandas_trata_como_nulo_ficam_texto(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("v\nNA\nnull\nN/A\nNaN\n", encoding="utf-8")
    assert ingestao.ler_arquivo(p)["v"].tolist() == ["NA", "null", "N/A", "NaN"]

def test_campo_vazio_e_aspas_vazias_viram_nulo(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text('v\n\n""\nx\n', encoding="utf-8")
    assert ingestao.ler_arquivo(p)["v"].isna().tolist() == [True, True, False]

def test_utf8_com_acento_e_virgula_entre_aspas(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text('bairro,end\n"São Conrado","Rua A, 10"\n', encoding="utf-8")
    df = ingestao.ler_arquivo(p)
    assert df.loc[0, "bairro"] == "São Conrado"
    assert df.loc[0, "end"] == "Rua A, 10"

def test_todas_as_colunas_sao_texto(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("n\n1\n2\n", encoding="utf-8")
    assert ingestao.ler_arquivo(p).dtypes.tolist() == [object]
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `ler_arquivo` não definido.

- [ ] **Step 3: Implementar `MAPA` e `ler_arquivo`**

Assinaturas acima. Opções de `pd.read_csv` como na spec: `encoding="utf-8"`, `dtype=str`, `keep_default_na=False`, `na_values=[""]`.

- [ ] **Step 4: Rodar e ver passar**

Expected: os cinco testes PASS.


---

### Task 6: Verificação de arquivos antes do banco

**Files:**
- Modify: `tests/test_ingestao.py`
- Modify: `src/pipeline/ingestao.py`

**Interfaces:**
- Consumes: `MAPA` e `ler_arquivo` (Task 5); `conectar` (Task 4).
- Produces:
  - `RAW_DIR: Path` = pasta `data/raw` do projeto.
  - `arquivos_faltantes(pasta: Path) -> list[str]`: nomes de `MAPA` que não existem em `pasta`, na ordem de `MAPA`.
  - `main(pasta: Path = RAW_DIR, conectar_fn=conectar) -> int`: se houver faltantes, imprime cada um, imprime `pasta`, devolve 1 sem chamar `conectar_fn`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_faltantes_lista_os_que_faltam(tmp_path):
    (tmp_path / "listings.csv.gz").write_bytes(b"")
    assert ingestao.arquivos_faltantes(tmp_path) == [
        "calendar.csv.gz", "reviews.csv.gz", "neighbourhoods.csv",
    ]

def test_main_para_antes_de_conectar(tmp_path, capsys):
    chamadas = []
    def fake_conectar():
        chamadas.append(1)
    assert ingestao.main(pasta=tmp_path, conectar_fn=fake_conectar) == 1
    assert chamadas == []
    saida = capsys.readouterr().out
    assert "listings.csv.gz" in saida and str(tmp_path) in saida
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

`arquivos_faltantes` e a verificação no início de `main`. `main` também faz `sys.stdout.reconfigure(encoding="utf-8")` antes de imprimir.

- [ ] **Step 4: Rodar e ver passar**

Expected: os dois testes PASS.


---

### Task 7: Ingestão em transação, saída e banco em uso

**Files:**
- Modify: `tests/test_ingestao.py`
- Modify: `src/pipeline/ingestao.py`

**Interfaces:**
- Consumes: `MAPA`, `ler_arquivo` (Task 5); `arquivos_faltantes`, `main` (Task 6); `gravar` (Task 4).
- Produces:
  - `formatar_contagem(n: int) -> str`: milhar com ponto (`1550922` → `"1.550.922"`).
  - `ingerir(con, pasta: Path) -> list[tuple[str, int]]`: grava cada tabela de `MAPA` numa única transação (`con.begin()`, `con.commit()`, e `con.rollback()` em caso de exceção); devolve `(tabela, contagem)` na ordem de `MAPA`.
  - `main` passa a imprimir uma linha por tabela e uma linha de total; em `duckdb.Error` ao conectar ou gravar, imprime mensagem que cita o explorador (`ui`) e devolve 1.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_formata_milhar_com_ponto():
    assert ingestao.formatar_contagem(1550922) == "1.550.922"
    assert ingestao.formatar_contagem(999) == "999"

def test_saida_uma_linha_por_tabela_e_total(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")   # helper do arquivo de testes
    assert ingestao.main(pasta=tmp_path / "raw") == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert len(linhas) == 5
    assert linhas[-1].startswith("total")

def test_duas_execucoes_imprimem_o_mesmo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    ingestao.main(pasta=tmp_path / "raw")
    primeira = capsys.readouterr().out
    ingestao.main(pasta=tmp_path / "raw")
    assert capsys.readouterr().out == primeira

def test_falha_no_meio_nao_deixa_parcial(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    (tmp_path / "raw" / "reviews.csv.gz").write_bytes(b"nao e gzip")  # quebra no 3º
    with pytest.raises(Exception):
        ingestao.ingerir(db.conectar(), tmp_path / "raw")
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    tabelas = con.execute("select table_name from information_schema.tables where table_schema='raw'").fetchall()
    assert tabelas == []
    con.close()

def test_banco_em_uso_falha_com_mensagem_e_codigo_1(tmp_path, capsys):
    def conectar_em_uso():
        raise duckdb.Error("Could not set lock on file")
    _criar_quatro_arquivos_pequenos(tmp_path / "raw")
    assert ingestao.main(pasta=tmp_path / "raw", conectar_fn=conectar_em_uso) == 1
    assert "ui" in capsys.readouterr().out
```

`_criar_quatro_arquivos_pequenos` é helper do próprio arquivo de teste: cria os quatro arquivos com uma linha de cabeçalho e uma de dados.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

`formatar_contagem`, `ingerir` e a versão final de `main`. Em `main`, `conectar_fn` é chamado dentro de `try` que captura `duckdb.Error` e devolve 1 com a mensagem. Em `ingerir`, `con.begin()` antes do laço, `con.commit()` depois, e `con.rollback()` no `except` seguido de `raise`.

- [ ] **Step 4: Rodar e ver passar**

Expected: todos os testes de `test_ingestao.py` PASS, e cobertura de `ingestao.py` mostrada no relatório.


---

### Task 8: Verificação manual da ingestão

**Files:** nenhum.

**Interfaces:**
- Consumes: `main` da Task 7 via `python -m pipeline.ingestao`.
- Produces: nada; é conferência.

- [ ] **Step 1: Adicionar o comando ao script**

Acrescentar `ingestao` ao `scripts\comandos_uv.bat` (`uv run python -m pipeline.ingestao`). Ver Task 11.

- [ ] **Step 2: Executar a ingestão**

Run (desenvolvedor): `scripts\comandos_uv.bat ingestao`
Expected: quatro linhas com `raw.anuncios`, `raw.calendario`, `raw.avaliacoes`, `raw.bairros` e a contagem vinda do banco; linha `total`; código de saída 0.

- [ ] **Step 3: Reexecutar**

Expected: saída idêntica à anterior.

- [ ] **Step 4: Conferir o tipo**

Run (desenvolvedor), com o DuckDB CLI ou uma linha Python: `SELECT * FROM raw.anuncios LIMIT 1`
Expected: todas as colunas como VARCHAR.

- [ ] **Step 5: Faltando um arquivo**

Renomear `data/raw/calendar.csv.gz`, rodar `ingestao`, desfazer o renome.
Expected: lista `calendar.csv.gz`, mostra a pasta, código 1, nenhuma tabela gravada nova.

---

### Task 9: Explorador, verificação do banco

**Files:**
- Create: `tests/test_ui.py`
- Modify: `src/ui/ui.py`

**Interfaces:**
- Consumes: nada do pacote `pipeline` (decisão U4).
- Produces:
  - `BANCO: Path` = `data/insideairbnb.duckdb` do projeto, calculado a partir de `__file__`.
  - `PORTA: int = 4213`.
  - `verificar_banco(caminho: Path) -> None`: se o arquivo não existe, imprime que é preciso rodar a ingestão antes e `sys.exit(1)`, sem criar nada.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_sem_banco_encerra_sem_criar_arquivo(tmp_path, capsys):
    alvo = tmp_path / "x.duckdb"
    with pytest.raises(SystemExit) as e:
        ui.verificar_banco(alvo)
    assert e.value.code == 1
    assert not alvo.exists()
    assert "ingest" in capsys.readouterr().out.lower()

def test_ui_nao_importa_pipeline():
    arvore = ast.parse(Path(ui.__file__).read_text(encoding="utf-8"))
    importados = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)}
    importados |= {a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and m.startswith("pipeline") for m in importados)
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar `BANCO`, `PORTA` e `verificar_banco`**

- [ ] **Step 4: Rodar e ver passar**

Expected: os dois testes PASS.


---

### Task 10: Explorador, subida do servidor e Ctrl+C

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `src/ui/ui.py`

**Interfaces:**
- Consumes: `BANCO`, `verificar_banco` (Task 9).
- Produces: `main(caminho: Path = BANCO, esperar: Callable[[], None] | None = None) -> int`.

**Comportamento, na ordem:**
1. `sys.stdout.reconfigure(encoding="utf-8")`.
2. `verificar_banco(caminho)`: sai com código 1 se o arquivo não existir.
3. `con = duckdb.connect(str(caminho))`.
4. `con.execute("INSTALL ui; LOAD ui;")`.
5. `con.execute("CALL start_ui()")`. Esta chamada sobe o servidor em `http://localhost:4213` e abre o navegador padrão sozinha. Nenhuma chamada de `webbrowser` no código.
6. Imprime a URL e `Ctrl+C para encerrar`.
7. Chama `esperar()`, que mantém o processo vivo até Ctrl+C.
8. `KeyboardInterrupt` é capturado: `con.close()` (isso também encerra o servidor) e `main` devolve 0, sem traceback.
9. Qualquer `duckdb.Error` nas etapas 3 a 5 imprime a mensagem e devolve 1. Isso cobre, por exemplo, a porta 4213 já ocupada.

**Porta:** não há configuração de porta no código. O padrão da extensão já é 4213, que é a porta da spec. Por isso não se chama `SET ui_local_port`. Se a porta estiver ocupada, a etapa 5 falha e a mensagem da etapa 9 aparece.

**Espera (`esperar` padrão):** laço com `time.sleep(1)` em `while True`. Usar `threading.Event().wait()` sem tempo limite pode não responder ao Ctrl+C no Windows.

- [ ] **Step 1: Escrever os testes que falham**

Fake de `duckdb.connect` via `monkeypatch` que registra cada `execute` e o `close`.

```python
def test_sequencia_de_chamadas(tmp_path, monkeypatch):
    banco = tmp_path / "x.duckdb"; banco.write_bytes(b"")
    chamadas = []
    class Fake:
        def execute(self, sql): chamadas.append(sql)
        def close(self): chamadas.append("close")
    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Fake())
    def ctrl_c(): raise KeyboardInterrupt
    assert ui.main(caminho=banco, esperar=ctrl_c) == 0
    assert chamadas == ["INSTALL ui; LOAD ui;", "CALL start_ui()", "close"]

def test_ctrl_c_fecha_e_sai_sem_excecao(tmp_path, monkeypatch):
    banco = tmp_path / "x.duckdb"; banco.write_bytes(b"")
    fechou = []
    class Fake:
        def execute(self, sql): pass
        def close(self): fechou.append(True)
    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Fake())
    def ctrl_c(): raise KeyboardInterrupt
    assert ui.main(caminho=banco, esperar=ctrl_c) == 0
    assert fechou == [True]

def test_erro_do_duckdb_devolve_1(tmp_path, monkeypatch, capsys):
    banco = tmp_path / "x.duckdb"; banco.write_bytes(b"")
    class Fake:
        def execute(self, sql): raise duckdb.Error("porta ocupada")
        def close(self): pass
    monkeypatch.setattr(ui.duckdb, "connect", lambda p: Fake())
    assert ui.main(caminho=banco, esperar=lambda: None) == 1
    assert "porta ocupada" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Run (desenvolvedor): `scripts\comandos_uv.bat test`
Expected: FAIL, `main` não definido.

- [ ] **Step 3: Implementar `main` conforme o comportamento acima**

- [ ] **Step 4: Rodar e ver passar**

Expected: os três testes PASS.


---

### Task 11: Comandos no script do uv

**Files:**
- Modify: `scripts/comandos_uv.bat` (Windows)
- Modify: `scripts/comandos_uv.sh` (Linux, mesmos comandos)

**Interfaces:**
- Consumes: nada.
- Produces: comandos `ingestao` (`uv run python -m pipeline.ingestao`) e `ui` (`uv run python src/ui/ui.py`), listados na ajuda.

- [ ] **Step 1: Acrescentar os dois comandos nos dois scripts**

Adicionar `if /I "%~1"=="ingestao" goto ingestao` e `ui` no bloco de despacho; adicionar as linhas de ajuda; adicionar `:ingestao` e `:ui` com os comandos.

- [ ] **Step 2: Verificar a ajuda**

Run (desenvolvedor): `scripts\comandos_uv.bat`
Expected: lista inclui `ingestao` e `ui`, e nenhum uv é executado.


---

### Task 12: Verificação manual do explorador

**Files:** nenhum.

**Interfaces:**
- Consumes: `main` da Task 10 via `scripts\comandos_uv.bat ui`.
- Produces: nada; é conferência.

- [ ] **Step 1: Subir o explorador**

Run (desenvolvedor): `scripts\comandos_uv.bat ui`
Expected: navegador abre em `localhost:4213`; schema `raw` com quatro tabelas.

- [ ] **Step 2: Ctrl+C**

Expected: terminal volta sem traceback.

- [ ] **Step 3: Ingestão logo depois**

Run: `scripts\comandos_uv.bat ingestao`
Expected: roda sem erro de lock.

- [ ] **Step 4: Sem banco**

Renomear `data/insideairbnb.duckdb`, rodar `ui`, desfazer o renome.
Expected: mensagem para rodar a ingestão antes, código 1, nenhum `.duckdb` criado.

---

### Task 13: Qualidade

**Files:** nenhum novo; ajustes pontuais onde o lint apontar.

**Interfaces:** nada.

- [ ] **Step 1: Lint**

Run (desenvolvedor): `scripts\comandos_uv.bat lint`
Expected: sem erros.

- [ ] **Step 2: Formatação**

Run: `scripts\comandos_uv.bat format`
Expected: arquivos formatados.

- [ ] **Step 3: Testes com cobertura**

Run: `scripts\comandos_uv.bat test`
Expected: todos PASS; relatório de cobertura no terminal com o percentual de `src/`. Registrar o percentual; limite mínimo é decisão posterior.

---

## Checklist de aceite (spec)

- [ ] `import pipeline.db` não cria nem abre banco (Task 3).
- [ ] `conectar()` de outra pasta cria o `.duckdb` em `data/` (Task 3).
- [ ] `gravar()` com 3 linhas devolve 3, duas vezes (Task 4).
- [ ] Ingestão imprime quatro linhas e o total; duas execuções saem iguais (Task 8).
- [ ] `SELECT * FROM raw.anuncios` devolve colunas VARCHAR (Task 8).
- [ ] Faltando um arquivo, para antes de gravar qualquer tabela (Tasks 6 e 8).
- [ ] Processo termina sozinho (Task 8).
- [ ] `ui` abre em `localhost:4213` com schema `raw` e quatro tabelas (Task 12).
- [ ] Ctrl+C sai sem traceback; ingestão roda depois sem erro de lock (Task 12).
- [ ] Sem banco, `ui` para com mensagem e não cria arquivo (Tasks 9 e 12).

## Fora deste plano

- Etapa 2 (staging), mart, Streamlit, MkDocs e GitHub Pages.
- Correção do `README.md` (decisão 5 do design).
