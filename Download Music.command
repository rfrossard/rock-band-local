#!/bin/bash
# ────────────────────────────────────────────────────────────
#  Fross Garage Band — Download Music
#  Duplo-clique para abrir o browser de músicas do Rhythmverse
# ────────────────────────────────────────────────────────────
cd "$(dirname "$0")"

VENV_PY=".venv/bin/python3"
SYS_PY=$(which python3 2>/dev/null)

if [ -f "$VENV_PY" ]; then
    PY="$VENV_PY"
elif [ -n "$SYS_PY" ]; then
    PY="$SYS_PY"
else
    osascript -e 'display alert "Python 3 não encontrado." message "Instale o Python 3 em python.org"'
    exit 1
fi

# Verificar dependências
$PY -c "import pygame, requests, bs4" 2>/dev/null || {
    echo "Instalando dependências..."
    $PY -m pip install pygame requests beautifulsoup4 --quiet
}

exec $PY download_music.py "$@"
