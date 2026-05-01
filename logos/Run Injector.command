#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Fross Garage Band — YARG Logo Injector launcher
#  Double-click this file in Finder to update YARG's logos.
# ─────────────────────────────────────────────────────────────

# Move to the folder that contains this script
cd "$(dirname "$0")"

VENV_PYTHON="../.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python environment not found at:"
    echo "  $(realpath "$VENV_PYTHON" 2>/dev/null || echo "$VENV_PYTHON")"
    echo ""
    echo "Set it up once with:"
    echo "  cd '$(dirname "$(pwd)")' && python3 -m venv .venv && .venv/bin/pip install UnityPy Pillow"
    read -p "Press Enter to close..."
    exit 1
fi

"$VENV_PYTHON" inject_logo.py
echo ""
read -p "Press Enter to close..."
