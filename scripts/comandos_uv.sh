#!/usr/bin/env bash
# Comandos do uv do projeto (Linux/bash). Versão de scripts/comandos_uv.bat.
# Cada execucao roda somente o comando pedido.
# Uso: scripts/comandos_uv.sh <comando>
# Sem argumento, so mostra a lista. Nada e executado automaticamente.

ajuda() {
    echo "Uso: scripts/comandos_uv.sh <comando>"
    echo
    echo "  init       cria o pyproject.toml (Python 3.13, sem arquivos de exemplo)"
    echo "  add-deps   adiciona duckdb e pandas; ruff, pytest e pytest-cov no grupo dev"
    echo "  sync       instala as dependencias do pyproject.toml"
    echo "  lint       ruff check"
    echo "  format     ruff format"
    echo "  test       pytest com coverage"
    echo "  venv       mostra como ativar o .venv neste terminal"
}

case "${1:-}" in
    "")
        ajuda
        ;;
    init)
        uv init --bare --python 3.13
        ;;
    add-deps)
        uv add duckdb pandas
        uv add --dev ruff pytest pytest-cov
        ;;
    sync)
        uv sync
        ;;
    lint)
        uv run ruff check .
        ;;
    format)
        uv run ruff format .
        ;;
    test)
        uv run pytest --cov=src --cov-report=term-missing
        ;;
    venv)
        echo "Linux/bash:  source .venv/bin/activate"
        echo "Para sair:   deactivate"
        echo
        echo 'Nao e preciso ativar: "uv run" usa o .venv sozinho.'
        echo
        RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
        if [ ! -f "$RAIZ/.venv/bin/activate" ]; then
            echo "Nao encontrei $RAIZ/.venv. Rode 'scripts/comandos_uv.sh sync' antes."
            return 1 2>/dev/null || exit 1
        fi
        if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
            # Chamado com 'source': ativa no terminal atual.
            # shellcheck disable=SC1091
            source "$RAIZ/.venv/bin/activate"
            echo "Ambiente .venv ativado neste terminal."
        else
            # Chamado como 'bash scripts/...': um processo filho nao ativa o terminal que o chamou.
            # Abre um novo bash com o .venv ativo; 'exit' volta ao terminal anterior.
            echo "Abrindo um novo bash com o .venv ativo (use 'exit' para voltar)."
            exec bash --rcfile <(printf '%s\n' '[ -f ~/.bashrc ] && . ~/.bashrc' ". \"$RAIZ/.venv/bin/activate\"") -i
        fi
        ;;
    *)
        echo "Comando desconhecido: $1"
        ajuda
        return 1 2>/dev/null || exit 1
        ;;
esac
