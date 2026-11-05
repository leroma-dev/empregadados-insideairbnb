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

:fim
endlocal
