#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Song Manager.command  —  duplo-clique no Finder ou arrasta pro Dock
# ─────────────────────────────────────────────────────────────────────────────
cd "$(dirname "$0")"

# ── Limpa vars do pyenv/virtualenv ────────────────────────────────────────────
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONNOUSERSITE
unset PYENV_VERSION PYENV_ROOT PYENV_DIR PYENV_HOOK_PATH VIRTUAL_ENV

# ── Encontra python3.11 ───────────────────────────────────────────────────────
PY=""
for candidate in \
    "$HOME/homebrew/Cellar/python@3.11"/*/Frameworks/Python.framework/Versions/3.11/bin/python3.11 \
    "$HOME/homebrew/bin/python3.11" \
    "/opt/homebrew/bin/python3.11" \
    "/usr/local/bin/python3.11"
do
  if [ -x "$candidate" ]; then
    PY="$candidate"
    break
  fi
done

if [ -z "$PY" ] && command -v python3.11 &>/dev/null; then
  PY="$(command -v python3.11)"
fi

if [ -z "$PY" ]; then
  echo "❌  python3.11 não encontrado."
  echo "    Instale com: brew install python@3.11 && brew install python-tk@3.11"
  read -p "Pressione Enter para fechar..."
  exit 1
fi

# ── Verifica tkinter ──────────────────────────────────────────────────────────
"$PY" -c "import tkinter" 2>/dev/null || {
  echo "❌  tkinter não encontrado."
  echo "    Execute: brew install python-tk@3.11"
  read -p "Pressione Enter para fechar..."
  exit 1
}

# ── Instala dependências se necessário ───────────────────────────────────────
"$PY" -c "import requests, bs4" 2>/dev/null || {
  echo "📦  Instalando dependências..."
  "$PY" -m pip install --quiet requests beautifulsoup4
}

# ── Lança ─────────────────────────────────────────────────────────────────────
echo "🎸  Fross Song Manager — Matrix Edition"
exec "$PY" song_manager.py
