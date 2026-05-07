#!/bin/bash
# ────────────────────────────────────────────────────────────
#  Fross Garage Band — Launch YARG
#  Double-click to start the game
# ────────────────────────────────────────────────────────────
YARG="/Applications/YARG.app"

if [ ! -d "$YARG" ]; then
    osascript -e 'display alert "YARG não encontrado" message "Certifique-se que YARG está instalado em /Applications/YARG.app"'
    exit 1
fi

open "$YARG"
