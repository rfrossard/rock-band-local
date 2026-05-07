#!/usr/bin/env bash
# Fross Song Manager — launcher macOS (duplo-clique no Finder)

cd "$(dirname "$0")"

# Prefere python3.11 do Homebrew (tem Tk 8.6), depois pyenv 3.10, depois sistema
if [ -x "$(brew --prefix python@3.11 2>/dev/null)/bin/python3.11" ]; then
  PY="$(brew --prefix python@3.11)/bin/python3.11"
elif command -v pyenv &>/dev/null && pyenv versions --bare 2>/dev/null | grep -q "3.10"; then
  PYENV_VERSION=3.10.6; export PYENV_VERSION
  PY="$(pyenv which python3 2>/dev/null)"
else
  PY="$(command -v python3)"
fi

if [ -z "$PY" ]; then
  osascript -e 'display alert "Python 3 não encontrado" message "Instale via: brew install python3" as critical'
  exit 1
fi

# Verifica tkinter (obrigatório)
"$PY" -c "import tkinter" 2>/dev/null || {
  osascript -e 'display alert "tkinter não encontrado" message "Execute: brew install python-tk" as critical'
  exit 1
}

# Instala dependências se necessário (silencioso)
"$PY" -c "import requests, bs4" 2>/dev/null || \
  "$PY" -m pip install --quiet requests beautifulsoup4

echo "🎸  Fross Song Manager"
exec "$PY" song_manager.py
