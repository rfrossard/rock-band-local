#!/usr/bin/env bash
# ============================================================
#  Rock Band Local — Script de instalação (macOS / Linux)
# ============================================================
set -e

PYTHON=python3

echo ""
echo "🎸  Rock Band Local — Instalação"
echo "=================================="

# Verifica Python
if ! command -v $PYTHON &>/dev/null; then
  echo "❌  Python 3 não encontrado. Instale em https://python.org"
  exit 1
fi

PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓  Python $PYVER detectado"

# Cria venv se não existir
if [ ! -d ".venv" ]; then
  echo "→  Criando ambiente virtual (.venv)..."
  $PYTHON -m venv .venv
fi

source .venv/bin/activate

echo "→  Instalando dependências principais..."
pip install --upgrade pip -q
pip install pygame requests beautifulsoup4 Pillow -q

echo "→  Tentando instalar dependências de áudio (vocal)..."
pip install numpy sounddevice -q && \
  pip install aubio -q && \
  echo "✓  Suporte a vocal instalado." || \
  echo "⚠️   aubio não instalado — vocal desativado (jogo funciona normalmente)."

echo ""
echo "✅  Instalação concluída!"
echo ""
echo "  Para jogar:"
echo "    source .venv/bin/activate"
echo "    python main.py"
echo ""
echo "  Coloque suas músicas (pastas com notes.chart) em: songs/"
echo "  Ou use o menu 🌐 Rhythmverse para baixar músicas online."
echo ""
