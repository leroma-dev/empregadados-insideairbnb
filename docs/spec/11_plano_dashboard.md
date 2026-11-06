# Dashboard Streamlit: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um dashboard Streamlit com duas páginas (anfitrião e investidor), cada indicador com uma explicação curta, lendo os nove marts do banco localmente e uma cópia exportada em Parquet para publicação.

**Architecture:** Um pacote `dashboard` em `src/dashboard/` com três camadas: leitura (`dados.py`, única que conhece a origem: banco ou Parquet), preparação dos números (funções puras, testadas), e apresentação (páginas Streamlit que só desenham). A exportação fica em `src/pipeline/publicacao.py` e grava `data/publicacao/*.parquet` mais `atualizacao.json`. Nenhuma conta de mart é refeita no app.

**Tech Stack:** Python 3.13, uv, DuckDB 2.0.0, Streamlit (grupo de dependências `dashboard`), pytest, ruff.

**Spec:** `docs/spec/10_dashboard_design.md` (status APROVADA). Este plano argumenta a partir dela; quem implementa lê as duas.

## Premissas (perguntas abertas da spec, decididas aqui)

As três perguntas da spec não foram respondidas. O plano segue as propostas da spec e isola o que depende da resposta:

- **Repositório público:** confirmado pelo autor. A publicação no Streamlit Community Cloud segue o caminho previsto.
- **Filtros:** sem filtros na primeira versão, confirmado pelo autor. Não há filtro em nenhuma tarefa.
- **Textos das explicações:** redigidos pelo construtor e marcados como "a aprovar". O autor aprova a redação antes da publicação (Task 8).

## Global Constraints

- Python 3.13; dependências com uv. Streamlit entra no grupo `dashboard`, separado do pipeline.
- Código em `src/dashboard/` (app e páginas) e `src/pipeline/publicacao.py` (exportação). Testes em `tests/`.
- O app só lê. Nenhuma escrita em `mart`, `staging` ou `raw`.
- A origem dos dados é escolhida em um lugar só (`dados.py`): banco local em modo somente leitura, ou Parquet em `data/publicacao/`.
- Nenhum mart é recalculado no app. Somas e médias que já estão no mart não são refeitas.
- Cada gráfico tem título, gráfico e uma explicação de no máximo três frases, sempre visível.
- Explicações incluem as ressalvas: ocupação conta bloqueios do anfitrião; receita é estimativa com o preço do anúncio para o ano; 2026 é período incompleto.
- Dados gerados (`data/publicacao/`) são versionados; o `.duckdb` nunca é versionado nem publicado.
- `sys.stdout.reconfigure(encoding="utf-8")` nos pontos de entrada Python.
- Testes usam `tmp_path`; nunca tocam no `.duckdb` real nem em `data/publicacao/` real.
- Comandos uv são rodados pelo desenvolvedor via `scripts/comandos_uv.sh <comando>`. Nenhum comando roda automaticamente.
- Commits no git são feitos pelo desenvolvedor; o plano não tem etapa de commit.

## Review Focus

1. Banco aberto por outro processo (o explorador `ui`): o app mostra mensagem clara e não cria arquivo. Pinned by Task 2.
2. `atualizacao.json` ausente ou com data inválida: o rodapé mostra "data desconhecida", e o app não quebra. Pinned by Task 4.
3. Mart com zero linhas (ex.: filtro sem resultado): a página mostra "sem dados" no lugar do gráfico, sem erro. Pinned by Task 5.
4. Bairro sem preço (anúncios sem `price` excluídos da mediana): o número não aparece como zero. Pinned by Task 5.
5. Texto de explicação vazio ou longo demais (mais de três frases): falha nos testes. Pinned by Task 4.

---

### Task 1: Esqueleto do pacote e dependência Streamlit

**Files:**
- Create: `src/dashboard/__init__.py` (vazio), `src/dashboard/paginas/__init__.py` (vazio)
- Modify: `pyproject.toml`
- Test: `tests/test_dashboard_import.py`

**Interfaces:**
- Consumes: nada.
- Produces: pacote importável `dashboard` (e `dashboard.paginas`) após `uv sync`; grupo `dashboard` com `streamlit`.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_pacote_dashboard_importa():
    import dashboard
    import dashboard.paginas
    assert dashboard is not None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `scripts/comandos_uv.sh test`
Expected: FAIL, `No module named dashboard`.

- [ ] **Step 3: Configurar**

Run (desenvolvedor): `uv add --group dashboard streamlit`. Em `pyproject.toml`, `[tool.hatch.build.targets.wheel] packages` passa a incluir `"src/dashboard"`. Criar os `__init__.py`.

- [ ] **Step 4: Rodar e ver passar**

Run: `scripts/comandos_uv.sh sync` e depois `scripts/comandos_uv.sh test`. Expected: PASS.

---

### Task 2: Camada de leitura (origem banco ou Parquet)

**Files:**
- Create: `src/dashboard/dados.py`
- Test: `tests/test_dashboard_dados.py`

**Interfaces:**
- Consumes: nada do projeto; `caminho_banco` de `pipeline.db` (só como padrão).
- Produces:
  - `MARTS: tuple[str, ...]`: os nove nomes, na ordem da spec de marts (`preco_bairro`, `ocupacao_bairro`, `receita_mensal_anuncio`, `multi_host`, `reviews_mensal`, `inteiro_vs_privado`, `superhost`, `amenities`, `sazonalidade_reviews`).
  - `PASTA_PUBLICACAO: Path` = `data/publicacao` da raiz do projeto.
  - `class ErroOrigem(Exception)`: mensagem clara (banco em uso, arquivo ausente).
  - `origem() -> str`: `"publicacao"` se `PASTA_PUBLICACAO / "atualizacao.json"` existir, senão `"banco"`. Variável `DASHBOARD_ORIGEM` (quando definida) tem prioridade.
  - `carregar(nome: str, origem_escolhida: str | None = None, caminho_banco: Path | None = None, pasta: Path = PASTA_PUBLICACAO) -> pd.DataFrame`: se banco, `SELECT * FROM mart.<nome>` em conexão somente leitura; se publicação, `SELECT * FROM read_parquet(...)` via DuckDB em memória. Nome fora de `MARTS` levanta `ValueError`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_carregar_do_parquet(tmp_path):
    duckdb.connect().execute(
        f"COPY (SELECT 1 AS x) TO '{tmp_path / 'preco_bairro.parquet'}' (FORMAT parquet)"
    )
    df = dados.carregar("preco_bairro", origem_escolhida="publicacao", pasta=tmp_path)
    assert df["x"].tolist() == [1]


def test_nome_fora_dos_marts_levanta(tmp_path):
    with pytest.raises(ValueError):
        dados.carregar("nao_existe", origem_escolhida="publicacao", pasta=tmp_path)


def test_banco_em_uso_vira_erro_claro(tmp_path, monkeypatch):
    # simula o lock do explorador: a conexão de leitura falha
    monkeypatch.setattr(dados, "_conectar_leitura", lambda p: (_ for _ in ()).throw(duckdb.IOException("Could not set lock")))
    with pytest.raises(dados.ErroOrigem):
        dados.carregar("preco_bairro", origem_escolhida="banco", caminho_banco=tmp_path / "x.duckdb")


def test_origem_publicacao_nao_abre_banco(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(dados, "_conectar_leitura", lambda p: chamadas.append(p))
    dados.carregar("preco_bairro", origem_escolhida="publicacao", pasta=tmp_path)
    assert chamadas == []


def test_origem_padrao_publicacao_quando_ha_atualizacao(tmp_path, monkeypatch):
    (tmp_path / "atualizacao.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dados, "PASTA_PUBLICACAO", tmp_path)
    monkeypatch.delenv("DASHBOARD_ORIGEM", raising=False)
    assert dados.origem() == "publicacao"
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL, `dados` não definido.

- [ ] **Step 3: Implementar**

`_conectar_leitura(caminho)` abre `duckdb.connect(str(caminho), read_only=True)` e é a única função que abre o banco, para que o teste possa substituí-la. Erros de `duckdb.Error` viram `ErroOrigem` com a sugestão de fechar o explorador.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 3: Exportação dos marts para Parquet

**Files:**
- Create: `src/pipeline/publicacao.py`
- Test: `tests/test_publicacao.py`

**Interfaces:**
- Consumes: `conectar`, `caminho_banco` de `pipeline.db`; `MARTS` de `dashboard.dados`; `formatar_contagem` de `pipeline.ingestao`.
- Produces:
  - `exportar(con, pasta: Path, nomes: tuple[str, ...]) -> list[tuple[str, int]]`: para cada mart, `COPY (SELECT * FROM mart.<nome>) TO '<pasta>/<nome>.parquet' (FORMAT parquet)`, e devolve `(nome, linhas)` com a contagem consultada no banco. Depois grava `atualizacao.json` com `{"gerado_em": "<ISO 8601 UTC>", "marts": {nome: linhas}}`.
  - `main(conectar_fn=conectar, pasta: Path = PASTA_PUBLICACAO) -> int`: imprime uma linha por mart e o total; devolve 1 se algum mart faltar (`mart` incompleto, rodar `uv run python -m pipeline.marts`), sem gravar arquivos parciais.
  - `if __name__ == "__main__": sys.exit(main())`.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_exporta_parquet_e_atualizacao(tmp_path, monkeypatch):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch)  # helper: mart.<nome> com 2 linhas cada
    resultado = publicacao.exportar(con, tmp_path / "pub", MARTS_TESTE)
    assert all(n == 2 for _, n in resultado)
    assert (tmp_path / "pub" / "preco_bairro.parquet").exists()
    assert json.loads((tmp_path / "pub" / "atualizacao.json").read_text())["marts"]["preco_bairro"] == 2


def test_mart_faltando_nao_grava_nada(tmp_path, monkeypatch):
    con = _banco_com_marts_minimos(tmp_path, monkeypatch, sem="multi_host")
    assert publicacao.main(conectar_fn=lambda: con, pasta=tmp_path / "pub") == 1
    assert not (tmp_path / "pub").exists() or not list((tmp_path / "pub").iterdir())
```

`MARTS_TESTE` é um tuplo pequeno de dois nomes no arquivo de teste.

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

Verificar a existência de todas as tabelas antes de escrever. Gravar em pasta temporária e mover ao final, para não deixar Parquet pela metade. Registrar `gerado_em` em UTC.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 4: Textos das explicações

**Files:**
- Create: `src/dashboard/textos.py`
- Test: `tests/test_dashboard_textos.py`

**Interfaces:**
- Consumes: nada.
- Produces: `TEXTOS: dict[str, Texto]` com chave por gráfico (`preco_bairro`, `ocupacao_bairro`, `receita_mensal`, `reviews_mensal`, `sazonalidade`, `inteiro_vs_privado`, `superhost`, `multi_host`, `amenities`). `Texto` é um `NamedTuple(titulo: str, explicacao: str)`. A redação segue a regra: até três frases, linguagem simples para anfitrião, com as ressalvas da spec.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_cada_grafico_tem_titulo_e_explicacao():
    for chave, texto in textos.TEXTOS.items():
        assert texto.titulo and texto.explicacao, chave


def test_explicacao_tem_no_maximo_tres_frases():
    for chave, texto in textos.TEXTOS.items():
        frases = [f for f in re.split(r"[.!?]+\s", texto.explicacao) if f.strip()]
        assert len(frases) <= 3, chave


def test_ocupacao_e_receita_trazem_as_ressalvas():
    assert "bloqueio" in textos.TEXTOS["ocupacao_bairro"].explicacao.lower()
    assert "estimat" in textos.TEXTOS["receita_mensal"].explicacao.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

Os textos são redigidos pelo construtor e marcados como "a aprovar" no comentário do módulo. A Task 8 é a aprovação do autor.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 5: Preparação dos números e páginas

**Files:**
- Create: `src/dashboard/preparo.py`, `src/dashboard/paginas/anfitriao.py`, `src/dashboard/paginas/investidor.py`
- Test: `tests/test_dashboard_preparo.py`

**Interfaces:**
- Consumes: `carregar`, `MARTS` (Task 2); `TEXTOS` (Task 4).
- Produces (em `preparo.py`, funções puras):
  - `top_bairros(df, coluna: str, minimo_anuncios: int = 100, n: int = 15) -> pd.DataFrame`: ordena por `coluna` decrescente, filtra por `anuncios_com_preco` ou `anuncios` ≥ `minimo_anuncios`, devolve as `n` primeiras.
  - `serie_receita_mensal(df) -> pd.DataFrame`: soma `receita_potencial` por `mes`.
  - `resumo_multi_host(df) -> dict`: `anfitrioes`, `multi_host`, `fatia_pct`.
  - Cada página é uma função `desenhar()` que chama `carregar`, prepara, e desenha com `st.bar_chart`/`st.line_chart`/`st.dataframe`, com `st.caption` vindo de `TEXTOS`. Se o DataFrame estiver vazio, mostra "sem dados".

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_top_bairros_filtra_minimo_e_ordena():
    df = pd.DataFrame({"bairro": ["A", "B", "C"], "preco_mediano": [10, 30, 20],
                       "anuncios_com_preco": [100, 5, 100]})
    assert preparo.top_bairros(df, "preco_mediano")["bairro"].tolist() == ["C", "A"]


def test_serie_receita_soma_por_mes():
    df = pd.DataFrame({"mes": ["2026-09-01", "2026-09-01"], "receita_potencial": [1.0, 2.0]})
    assert preparo.serie_receita_mensal(df)["receita_potencial"].tolist() == [3.0]


def test_df_vazio_nao_quebra():
    assert preparo.top_bairros(pd.DataFrame(columns=["bairro", "preco_mediano", "anuncios_com_preco"]), "preco_mediano").empty
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

Funções puras em `preparo.py`; páginas só desenham. Nenhum cálculo de mart nas páginas (Global Constraints).

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 6: Entrada do app, navegação e rodapé

**Files:**
- Create: `src/dashboard/app.py`
- Test: `tests/test_dashboard_app.py`

**Interfaces:**
- Consumes: `origem`, `PASTA_PUBLICACAO` (Task 2); páginas (Task 5).
- Produces: `src/dashboard/app.py` (ponto de entrada Streamlit): duas páginas, "Anfitrião" e "Investidor"; rodapé com "dados gerados em <data>" lido de `atualizacao.json`, ou "data desconhecida" se ausente ou inválido; indicador da origem (banco local ou publicação).

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_rodape_sem_atualizacao_diz_data_desconhecida(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "data desconhecida" in app_mod.texto_rodape()


def test_rodape_com_data_valida(tmp_path, monkeypatch):
    (tmp_path / "atualizacao.json").write_text('{"gerado_em": "2026-11-06T02:00:00Z"}', encoding="utf-8")
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "2026-11-06" in app_mod.texto_rodape()


def test_rodape_com_json_invalido_nao_quebra(tmp_path, monkeypatch):
    (tmp_path / "atualizacao.json").write_text("{não é json", encoding="utf-8")
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "data desconhecida" in app_mod.texto_rodape()
```

- [ ] **Step 2: Rodar e ver falhar**

Expected: FAIL.

- [ ] **Step 3: Implementar**

`texto_rodape()` é função pura, testada. `app.py` configura a página e chama `st.navigation`; cada página é um módulo de `paginas/`.

- [ ] **Step 4: Rodar e ver passar**

Expected: PASS.

---

### Task 7: Comandos no script do uv

**Files:**
- Modify: `scripts/comandos_uv.sh`
- Modify: `scripts/comandos_uv.bat`

**Interfaces:**
- Consumes: `main` de `pipeline.publicacao` (Task 3); `src/dashboard/app.py` (Task 6).
- Produces: comandos `publicacao` (`uv run python -m pipeline.publicacao`) e `dashboard` (`uv run streamlit run src/dashboard/app.py`), listados na ajuda, depois de `marts`.

- [ ] **Step 1: Acrescentar os comandos nos dois scripts**

No `.sh`: linhas de ajuda e casos `publicacao)` e `dashboard)`. No `.bat`: o equivalente, no padrão de `marts`.

- [ ] **Step 2: Verificar a ajuda**

Run: `scripts/comandos_uv.sh`
Expected: lista inclui `publicacao` e `dashboard`; nenhum uv é executado.

---

### Task 8: Publicação (bloqueada até as respostas do autor)

**Files:** nenhum no código; ação de publicação.

**Pré-condição:** a redação dos textos em `src/dashboard/textos.py` foi aprovada pelo autor. O repositório é público (confirmado).

- [ ] **Step 1: Confirmar a aprovação dos textos com o autor**

Expected: o autor aprovou a redação. Sem aprovação, não publicar.

- [ ] **Step 2: Exportar**

Run: `scripts/comandos_uv.sh publicacao`. Expected: nove Parquet e `atualizacao.json` em `data/publicacao/`, com as contagens de `mart.*`.

- [ ] **Step 3: Publicar**

Conectar o repositório no Streamlit Community Cloud, apontando para `src/dashboard/app.py`. Expected: a página pública abre e o rodapé mostra a data de geração.

---

### Task 9: Execução local e conferência

**Files:** nenhum.

**Interfaces:**
- Consumes: `scripts/comandos_uv.sh dashboard` (Task 7), `scripts/comandos_uv.sh publicacao` (Task 7).

- [ ] **Step 1: Exportar e conferir os totais**

Run: `scripts/comandos_uv.sh publicacao`. Conferir contra a spec de marts: MA2 (44.147), MA5 (26.869 anfitriões; 6.411 multi-host), MA6 (1.461.658 reviews), MA8 e MA9 (48.247).

- [ ] **Step 2: Rodar o app localmente**

Run: `scripts/comandos_uv.sh dashboard`. Expected: o navegador abre em `localhost:8501`, as duas páginas carregam, cada gráfico tem explicação visível, o rodapé mostra a data. Fechar o explorador `ui` antes, para não haver lock.

- [ ] **Step 3: Conferir a origem publicada**

Com `DASHBOARD_ORIGEM=publicacao`, as páginas carregam só de `data/publicacao/`. O teste `test_origem_publicacao_nao_abre_banco` (Task 2) já garante que o banco não é aberto nessa origem; nenhum arquivo precisa ser movido.

## Checklist de aceite (plano)

- [ ] Task 1 a Task 6: testes de `tests/` do dashboard PASS.
- [ ] Cobertura de `src/dashboard/` e `src/pipeline/publicacao.py` reportada por `scripts/comandos_uv.sh test`.
- [ ] Task 7: `publicacao` e `dashboard` aparecem na ajuda dos dois scripts.
- [ ] Task 8: textos aprovados pelo autor antes de publicar.
- [ ] Task 9: totais de exportação batem com a spec de marts; app local carrega as duas páginas.
- [ ] Docstring de `dados.py` e `publicacao.py` com o motivo de cada regra.
