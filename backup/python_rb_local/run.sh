#!/bin/bash
# Rock Band Local — launcher
cd "$(dirname "$0")"

# Criar venv se não existir
if [ ! -f ".venv/bin/python3" ]; then
  echo "🔧  Criando ambiente virtual..."
  python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
  echo "📦  Instalando dependências..."
  .venv/bin/pip install -q pygame requests beautifulsoup4 numpy
  .venv/bin/pip install -q sounddevice aubio 2>/dev/null || true
fi

echo "🎸  Rock Band Local — iniciando..."
exec .venv/bin/python3 main.py
