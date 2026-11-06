@echo off
rem Comandos do uv do projeto. Cada execucao roda somente o comando pedido.
rem Uso: scripts\comandos_uv.bat <comando>
rem Sem argumento, so mostra a lista. Nada e executado automaticamente.

if "%~1"=="" goto ajuda
if /I "%~1"=="init" goto init
if /I "%~1"=="add-deps" goto add_deps
if /I "%~1"=="sync" goto sync
if /I "%~1"=="lint" goto lint
if /I "%~1"=="format" goto format
if /I "%~1"=="test" goto test
if /I "%~1"=="venv" goto venv
if /I "%~1"=="ingestao" goto ingestao
if /I "%~1"=="ui" goto ui
if /I "%~1"=="mcp-duckdb" goto mcp_duckdb
echo Comando desconhecido: %~1
goto ajuda

:ajuda
echo Uso: scripts\comandos_uv.bat ^<comando^>
echo.
echo   init       cria o pyproject.toml (Python 3.13, sem arquivos de exemplo)
echo   add-deps   adiciona duckdb e pandas; ruff, pytest e pytest-cov no grupo dev
echo   sync       instala as dependencias do pyproject.toml
echo   lint       ruff check
echo   format     ruff format
echo   test       pytest com coverage
echo   venv       mostra como ativar o .venv neste terminal
echo   ingestao   grava as tabelas raw no banco (uv run python -m pipeline.ingestao)
echo   ui         abre o explorador do banco no navegador (uv run python src/ui/ui.py)
echo   mcp-duckdb registra o servidor MCP do DuckDB neste projeto (claude mcp add)
goto fim

:init
uv init --bare --python 3.13
goto fim

:add_deps
uv add duckdb pandas
uv add --dev ruff pytest pytest-cov
goto fim

:sync
uv sync
goto fim

:lint
uv run ruff check .
goto fim

:format
uv run ruff format .
goto fim

:test
uv run pytest --cov=src --cov-report=term-missing
goto fim

:venv
echo Prompt de Comando (cmd):  .venv\Scripts\activate.bat
echo PowerShell:               .venv\Scripts\Activate.ps1
echo Para sair:                deactivate
echo.
echo Nao e preciso ativar: "uv run" usa o .venv sozinho.
echo.
if not exist ".venv\Scripts\activate.bat" (
    echo Nao encontrei .venv. Rode "scripts\comandos_uv.bat sync" antes.
    goto fim
)
rem Um script nao ativa o cmd que o chamou: abre um novo cmd com o .venv ativo.
rem 'exit' nesse cmd volta ao terminal anterior.
echo Abrindo um novo cmd com o .venv ativo (use exit para voltar).
cmd /k ".venv\Scripts\activate.bat"
goto fim

:ingestao
uv run python -m pipeline.ingestao
goto fim

:ui
uv run python src/ui/ui.py
goto fim

:mcp_duckdb
rem Caminho do banco deste projeto; o exemplo original citava olist.duckdb.
claude mcp add --scope project duckdb -- uvx mcp-server-motherduck --db-path data/insideairbnb.duckdb
goto fim

:fim
endlocal
