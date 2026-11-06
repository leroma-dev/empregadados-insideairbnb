# Staging: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar as quatro tabelas `staging.*` a partir de `raw.*`, aplicando as conversões de tipo, a regra de duplicatas e as validações da spec, com saída na tela e falha limpa.

**Architecture:** Um módulo `pipeline.staging` com funções pequenas e testáveis: validação por expressão regular antes de cada conversão, conversão em SQL (`CAST`), remoção de linhas repetidas por `DISTINCT`, e uma função `transformar` que grava as quatro tabelas numa única transação. `pipeline.db` e `pipeline.ingestao` são reaproveitados sem alteração.

**Tech Stack:** Python 3.13, uv, DuckDB 2.0.0 (já no `pyproject.toml`), pytest, pytest-cov, ruff.

**Spec:** `docs/spec/06_staging_spec.md` (status APROVADA). Este plano argumenta a partir dela; quem implementa lê as duas.

## Global Constraints

- Python 3.13; dependências gerenciadas com uv.
- Banco: `data/insideairbnb.duckdb`; leitura de `raw.*`; escrita apenas em `staging.*`. Nunca escrever em `raw`.
- Conversão em SQL no DuckDB (`CAST`). Proibido `TRY_CAST`, `try_strptime` e qualquer conversão que transforme falha em nulo.
- Conversão que falha: diz tabela, coluna e um exemplo do valor, e encerra com `sys.exit(1)`.
- Nenhuma linha some por ter nulo; nenhum nulo é preenchido. Vazio em `raw` já é NULL.
- Linhas só saem pela regra de DUPLICATAS (linha inteira repetida), e cada saída é contada.
- Chave repetida com conteúdo diferente: para com `sys.exit(1)`; não escolhe uma linha.
- As quatro tabelas são gravadas numa única transação; falha em qualquer uma não altera nenhuma.
- `CREATE OR REPLACE TABLE`: rodar duas vezes dá o mesmo resultado.
- Nomes de colunas não mudam: `staging` tem os mesmos nomes de `raw`.
- Tipos por coluna: seção "Definições estruturadas" da spec. Colunas sem regra ficam VARCHAR.
- `sys.stdout.reconfigure(encoding="utf-8")` no ponto de entrada.
- Testes em `tests/test_staging.py` usam `tmp_path` e `monkeypatch` em `db.caminho_banco`; nunca tocam em `data/raw/` nem no `.duckdb` real.
- Comandos uv são rodados pelo desenvolvedor via `scripts/comandos_uv.sh <comando>`. Nenhum comando roda automaticamente.
- Commits no git são feitos pelo desenvolvedor; o plano não tem etapa de commit.

## Review Focus

1. `price` com mais de 2 casas decimais (ex.: `$314.005`) para com erro e não é arredondado. Pinned by Task 3.
2. `price` com vírgula de milhar (`$1,234.56`) converte para 1234.56, e não é erro. Pinned by Task 3.
3. Booleano fora de `t`/`f` (ex.: `T`, `yes`) para com erro; vazio continua NULL. Pinned by Task 3.
4. Texto como `NA` ou `null` em coluna VARCHAR permanece texto, sem conversão. Pinned by Task 3.
5. Linha repetida com NULL em alguma coluna é considerada igual (NULL = NULL) e conta como repetida. Pinned by Task 4.

---

### Task 1: Esqueleto do módulo e mapa de colunas

**Files:**
- Create: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: nada (a spec é a fonte).
- Produces:
  - `REGRAS: dict[str, list[tuple[str, str]]]`: por tabela de staging, lista de `(coluna, regra)`, com regra em `{"texto", "bigint", "integer", "double", "decimal_preco", "boolean", "data"}`. Coluna com regra `"texto"` passa sem conversão.
  - `CHAVES: dict[str, tuple[str, ...]]`: chave de cada tabela, em `raw` (nomes de coluna iguais).
  - `TABELAS: tuple[str, ...]` = `("anuncios", "calendario", "avaliacoes", "bairros")`.

- [ ] **Step 1: Escrever o teste que falha**

```python
from pipeline import staging


def test_mapa_cobre_as_quatro_tabelas_com_contagem_de_colunas():
    assert staging.TABELAS == ("anuncios", "calendario", "avaliacoes", "bairros")
    assert len(staging.REGRAS["anuncios"]) == 90
    assert len(staging.REGRAS["calendario"]) == 5
    assert len(staging.REGRAS["avaliacoes"]) == 6
    assert len(staging.REGRAS["bairros"]) == 2


def test_chaves_existem_nas_regras():
    for tabela, chave in staging.CHAVES.items():
        nomes = [c for c, _ in staging.REGRAS[tabela]]
        assert all(k in nomes for k in chave)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/comandos_uv.sh test`
Expected: FAIL, `staging` sem `REGRAS`.

- [ ] **Step 3: Criar `src/pipeline/staging.py`**

Docstring no topo com a spec resumida e o motivo de cada regra (entregável da spec). Definir `TABELAS`, `REGRAS` e `CHAVES` a partir das seções "Regras por tabela" e "Definições estruturadas" da spec. Copiar os nomes exatamente como estão em `raw`. Não criar funções ainda.

- [ ] **Step 4: Rodar e ver passar**

Expected: os dois testes PASS.

---

### Task 2: Validação por expressão regular

**Files:**
- Modify: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: `REGRAS` (Task 1); `conectar` e `gravar` de `pipeline.db` (usados nos testes com `tmp_path`).
- Produces:
  - `PADROES: dict[str, str]`: regra → expressão regular completa. `bigint` e `integer`: `-?[0-9]+`. `double`: `-?[0-9]+(\.[0-9]+)?`. `boolean`: `[tf]`. `data`: `[0-9]{4}-[0-9]{2}-[0-9]{2}`. `decimal_preco`: `\$([0-9]{1,3}(,[0-9]{3})*|[0-9]{1,8})\.[0-9]{2}`. Regras `texto` não têm padrão.
  - `primeiro_invalido(con, nome_raw: str, coluna: str, regra: str) -> str | None`: devolve o primeiro valor não NULL que não casa com o padrão, ou `None`. Usa `regexp_full_match`, nunca `TRY_CAST`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_primeiro_invalido_devolve_none_quando_tudo_casa(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["t", "f", None]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") is None


def test_primeiro_invalido_devolve_o_valor_que_nao_casa(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["t", "T", "f"]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") == "T"
```

Helper `_banco_com_raw(tmp_path, monkeypatch, colunas: dict[str, list])` cria `raw.teste` com `db.gravar` sobre `tmp_path / "t.duckdb"`. Escrever o helper no próprio arquivo de teste.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `primeiro_invalido` não definido.

- [ ] **Step 3: Implementar `PADROES` e `primeiro_invalido`**

Uma consulta: `SELECT col FROM {tabela} WHERE col IS NOT NULL AND NOT regexp_full_match(col, '{padrao}') LIMIT 1`. `tabela` e `col` vêm das constantes internas, nunca de entrada externa.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 3: Conversão de uma tabela

**Files:**
- Modify: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: `REGRAS`, `PADROES`, `primeiro_invalido` (Tasks 1 e 2).
- Produces:
  - `class ErroConversao(Exception)`: atributos `tabela: str`, `coluna: str`, `exemplo: str`.
  - `expressao_sql(coluna: str, regra: str) -> str`: expressão de `SELECT` para a coluna. `texto` → o nome da coluna. `bigint` → `CAST(col AS BIGINT)`. `integer` → `CAST(col AS INTEGER)`. `double` → `CAST(col AS DOUBLE)`. `decimal_preco` → `CAST(replace(replace(col, '$', ''), ',', '') AS DECIMAL(10,2))`. `boolean` → `CASE col WHEN 't' THEN true WHEN 'f' THEN false END`. `data` → `CAST(col AS DATE)`. Nome de saída igual ao da coluna.
  - `converter(con, tabela: str) -> None`: para cada coluna com regra diferente de `texto`, roda `primeiro_invalido`; se achar valor, levanta `ErroConversao`. Só depois de validar todas as colunas da tabela, executa a conversão (ver Task 4 para a fonte das linhas).

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_price_com_virgula_de_milhar_converte(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"price": ["$1,234.56"]})
    assert con.execute(f"SELECT {staging.expressao_sql('price', 'decimal_preco')} FROM raw.teste").fetchall() == [
        (1234.56,)
    ]


def test_price_com_tres_casas_decimais_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"price": ["$314.005"]})
    assert staging.primeiro_invalido(con, "raw.teste", "price", "decimal_preco") == "$314.005"


def test_boolean_inesperado_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["yes"]})
    assert staging.primeiro_invalido(con, "raw.teste", "x", "boolean") == "yes"


def test_texto_na_fica_texto(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"x": ["NA"]})
    assert con.execute(f"SELECT {staging.expressao_sql('x', 'texto')} FROM raw.teste").fetchall() == [("NA",)]
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `expressao_sql` não definido.

- [ ] **Step 3: Implementar `ErroConversao`, `expressao_sql` e `converter`**

Use a tabela do item "Produces" para as expressões. `converter` levanta `ErroConversao(tabela, coluna, exemplo)` na primeira coluna inválida. Não use `try/except` em volta de `CAST` para mascarar erro: se o `CAST` falhar por overflow, deixe `duckdb.Error` subir; a validação por padrão já cobre os casos de `price`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 4: Duplicatas

**Files:**
- Modify: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: `CHAVES` (Task 1); `ErroConversao` (Task 3).
- Produces:
  - `class ErroChaveConflitante(Exception)`: atributos `tabela: str`, `chave: tuple`, `linhas: list[tuple]`.
  - `linhas_repetidas(con, tabela_raw: str) -> int`: `count(*)` − `count(*)` de `SELECT DISTINCT *`.
  - `remover_repetidas(con, tabela_raw: str, chave: tuple[str, ...]) -> int`: verifica conflito de chave sobre `SELECT DISTINCT *` (ver regra abaixo) e devolve a quantidade de linhas removidas. Não grava nada; a escrita é da Task 5.
  - Verificação de chave: `SELECT chave, count(*) FROM (SELECT DISTINCT * FROM {raw}) WHERE chave IS NOT NULL GROUP BY chave HAVING count(*) > 1`. Se houver resultado, levanta `ErroChaveConflitante` com a primeira chave e as linhas conflitantes.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_linha_inteira_repetida_sai_e_e_contada(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": ["a", "a"]})
    assert staging.linhas_repetidas(con, "raw.teste") == 1


def test_null_igual_a_null_conta_como_repetida(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": [None, None]})
    assert staging.linhas_repetidas(con, "raw.teste") == 1


def test_mesma_chave_com_conteudo_diferente_para_com_erro(tmp_path, monkeypatch):
    con = _banco_com_raw(tmp_path, monkeypatch, {"id": ["1", "1"], "v": ["a", "b"]})
    with pytest.raises(staging.ErroChaveConflitante) as e:
        staging.remover_repetidas(con, "raw.teste", chave=("id",))
    assert e.value.chave == ("1",)
    assert len(e.value.linhas) == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

Chave nula não entra na verificação de conflito (`WHERE chave IS NOT NULL`): nulo não apaga linha nem vira conflito. Não sobrescrever `staging` aqui; a escrita é da Task 5.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 5: Transformação completa em transação única

**Files:**
- Modify: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: `converter`, `expressao_sql` (Task 3); `remover_repetidas`, `ErroChaveConflitante` (Task 4); `REGRAS`, `CHAVES`, `TABELAS` (Task 1).
- Produces:
  - `faltantes_raw(con) -> list[str]`: nomes de `TABELAS` cujas tabelas `raw.<nome>` não existem.
  - `transformar(con) -> list[tuple[str, int, int]]`: para cada tabela, na ordem de `TABELAS`, devolve `(tabela, linhas_em_staging, linhas_removidas)`. Tudo numa transação (`con.begin()`, `con.commit()`, `con.rollback()` + `raise` no erro), como em `ingestao.ingerir`. Cria o schema com `CREATE SCHEMA IF NOT EXISTS staging`. Cada tabela com `CREATE OR REPLACE TABLE staging.<t> AS SELECT <expressões> FROM (SELECT DISTINCT * FROM raw.<t>)`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_transformar_grava_quatro_tabelas_e_conta(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)  # helper: cria raw.* com 1 linha valida cada
    resultado = staging.transformar(con)
    assert [t for t, _, _ in resultado] == list(staging.TABELAS)
    assert all(removidas == 0 for _, _, removidas in resultado)


def test_falha_em_uma_tabela_nao_altera_nenhuma(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(tmp_path, monkeypatch, invalido_em=("calendario", "available", "maybe"))
    with pytest.raises(staging.ErroConversao):
        staging.transformar(con)
    tabelas = con.execute("select table_name from information_schema.tables where table_schema='staging'").fetchall()
    assert tabelas == []


def test_duas_execucoes_dao_o_mesmo_resultado(tmp_path, monkeypatch):
    con = _banco_com_quatro_raw(tmp_path, monkeypatch)
    primeira = staging.transformar(con)
    assert staging.transformar(con) == primeira
```

`_banco_com_quatro_raw` cria as quatro tabelas `raw.*` com uma linha válida cada, usando as colunas de `REGRAS`. Aceita `invalido_em=(tabela, coluna, valor)` para injetar um valor ruim. Escrever no próprio arquivo de teste.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar `faltantes_raw` e `transformar`**

Ordem dentro de `transformar`: validar todas as tabelas antes de criar qualquer uma (`converter` em cada tabela), depois criar as quatro. Assim a falha de conversão acontece antes de qualquer escrita, e a transação cobre a escrita.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 6: Saída na tela, erro de raw faltando e ponto de entrada

**Files:**
- Modify: `src/pipeline/staging.py`
- Test: `tests/test_staging.py`

**Interfaces:**
- Consumes: `transformar`, `faltantes_raw`, `ErroConversao`, `ErroChaveConflitante` (Task 5); `conectar` de `pipeline.db`; `formatar_contagem` de `pipeline.ingestao` (reuso, não reimplementar).
- Produces:
  - `main(conectar_fn=conectar) -> int`.
  - Saída, uma linha por tabela: `f"staging.{tabela:<12} {milhar(n)} linhas ({milhar(removidas)} duplicatas)"`. Abaixo, indentada, `"    nulos mantidos: "` seguido de `coluna contagem` separados por vírgula, só para colunas com nulo acima de zero. Última linha: `total` com a soma das linhas.
  - Erro de conversão ou de chave: imprime a mensagem (tabela, coluna, exemplo ou chave e linhas) e devolve 1.
  - Raw faltando: lista as tabelas, diz para rodar `uv run python -m pipeline.ingestao`, devolve 1, sem criar tabela.
  - `if __name__ == "__main__": sys.exit(main())`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_saida_uma_linha_por_tabela_e_total(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_raw_no_arquivo(tmp_path / "t.duckdb")  # helper
    assert staging.main() == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert linhas[-1].startswith("total")
    assert sum(1 for l in linhas if l.startswith("staging.")) == 4


def test_raw_faltando_lista_e_encerra_sem_criar(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    assert staging.main() == 1
    assert "pipeline.ingestao" in capsys.readouterr().out
    assert not (tmp_path / "t.duckdb").exists() or _sem_schema_staging(tmp_path / "t.duckdb")


def test_erro_de_conversao_imprime_tabela_coluna_e_exemplo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "caminho_banco", lambda: tmp_path / "t.duckdb")
    _criar_quatro_raw_no_arquivo(tmp_path / "t.duckdb", invalido_em=("calendario", "available", "maybe"))
    assert staging.main() == 1
    saida = capsys.readouterr().out
    assert "calendario" in saida and "available" in saida and "maybe" in saida
```

`_criar_quatro_raw_no_arquivo` e `_sem_schema_staging` são helpers do arquivo de teste.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar `main`**

`sys.stdout.reconfigure(encoding="utf-8")` no início de `main`. Verificar `faltantes_raw` antes de `conectar_fn()`. Contagem de nulos por coluna: uma consulta por tabela com `count(*) FILTER (WHERE col IS NULL)`. Milhar com `formatar_contagem`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 7: Comando no script do uv

**Files:**
- Modify: `scripts/comandos_uv.sh`
- Modify: `scripts/comandos_uv.bat`

**Interfaces:**
- Consumes: `main` da Task 6.
- Produces: comando `staging` (`uv run python -m pipeline.staging`), listado na ajuda.

- [ ] **Step 1: Acrescentar o comando nos dois scripts**

Em `comandos_uv.sh`: linha de ajuda `staging` e `staging)` no `case` com `uv run python -m pipeline.staging`. Em `comandos_uv.bat`: o equivalente, no padrão de `ingestao`.

- [ ] **Step 2: Verificar a ajuda**

Run: `scripts/comandos_uv.sh`
Expected: lista inclui `staging`, e nenhum uv é executado.

---

### Task 8: Execução real e critérios de aceite

**Files:** nenhum.

**Interfaces:**
- Consumes: `scripts/comandos_uv.sh staging` (Task 7).
- Produces: nada; é conferência contra a spec.

- [ ] **Step 1: Pré-condição**

Expected: `raw` com as quatro tabelas (`scripts/comandos_uv.sh ingestao` já rodado). Fechar o explorador (`ui`) antes; ele segura o lock do banco.

- [ ] **Step 2: Executar**

Run: `scripts/comandos_uv.sh staging`
Expected: quatro linhas, `anuncios` 48.247, `calendario` 17.610.155, `avaliacoes` 1.461.658, `bairros` 160; duplicatas 0 em todas; total 19.120.220; código de saída 0.

- [ ] **Step 3: Reexecutar**

Expected: saída idêntica à anterior (CA12, CA13).

- [ ] **Step 4: Conferir os critérios da spec**

Rodar as consultas dos critérios CA1 a CA11 no banco, em modo somente leitura, e comparar com a spec:
- CA3: `count(*) − count(DISTINCT chave) = 0` nas quatro tabelas.
- CA5: `DESCRIBE staging.<tabela>` contra a seção "Definições estruturadas".
- CA6: nulos por coluna iguais entre `raw` e `staging`.
- CA7: `price` em `staging.anuncios` tem a soma e o maior valor iguais aos medidos (maior 587.008,00; 44.147 não nulos).
- CA11: LEFT JOIN de órfãos = 0 para `listing_id` (avaliacoes e calendario) e `neighbourhood_cleansed`.

Expected: todos batem. Qualquer divergência vira correção no código antes de dar a etapa como concluída.

## Checklist de aceite (plano)

- [ ] Task 1 a Task 6: testes de `tests/test_staging.py` PASS.
- [ ] Cobertura de `src/pipeline/staging.py` reportada por `scripts/comandos_uv.sh test`.
- [ ] Task 7: `staging` aparece na ajuda dos dois scripts.
- [ ] Task 8: execução real bate com as contagens da spec; critérios CA1 a CA11 conferidos.
- [ ] Docstring do `staging.py` tem o motivo de cada regra (Entregáveis da spec).
