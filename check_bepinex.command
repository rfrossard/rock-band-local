#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "🔍  Diagnóstico BepInEx + Fix Repos Key"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

YARG="/Applications/YARG.app"
LOG="$YARG/BepInEx/LogOutput.log"
LANG_DIR="$YARG/Contents/Resources/Data/StreamingAssets/lang"

# ── 1. Verificar se BepInEx está instalado ─────────────
echo "[ 1/4 ] Verificando instalação BepInEx..."
if [ -f "$YARG/run_bepinex.sh" ]; then
    echo "  ✓ run_bepinex.sh existe"
else
    echo "  ✗ run_bepinex.sh NÃO encontrado!"
fi

if [ -f "$YARG/BepInEx/core/BepInEx.dll" ]; then
    echo "  ✓ BepInEx.dll existe"
else
    echo "  ✗ BepInEx.dll NÃO encontrado!"
fi

if [ -f "$YARG/BepInEx/plugins/FrossDownloadMusic/FrossDownloadMusic.dll" ]; then
    echo "  ✓ FrossDownloadMusic.dll existe ($(du -h "$YARG/BepInEx/plugins/FrossDownloadMusic/FrossDownloadMusic.dll" | cut -f1))"
else
    echo "  ✗ FrossDownloadMusic.dll NÃO encontrado!"
fi

# ── 2. Verificar log do BepInEx ────────────────────────
echo ""
echo "[ 2/4 ] Verificando log BepInEx..."
if [ -f "$LOG" ]; then
    echo "  ✓ LogOutput.log existe ($(du -h "$LOG" | cut -f1))"
    echo ""
    echo "  Últimas 30 linhas do log:"
    tail -30 "$LOG" | sed 's/^/    /'
else
    echo "  ✗ LogOutput.log NÃO existe"
    echo "  → O jogo foi lançado via YARG.app diretamente (sem BepInEx)"
    echo "  → Use: /Applications/Fross\\ Garage\\ Band.app para lançar com BepInEx"
fi

# ── 3. Fix: restaurar chave YARG no Repos ─────────────
echo ""
echo "[ 3/4 ] Corrigindo chave 'Fross Garage Band' no Repos..."
python3 << 'PYEOF'
import re, glob, os

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"
fixed = 0

for path in sorted(glob.glob(os.path.join(LANG_DIR, "*.json"))):
    fname = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        raw = f.read()
    original = raw

    # The regex renamed "YARG" key (inside Repos) → "Fross Garage Band"
    # Pattern: "Fross Garage Band": { (inside Repos context, but hard to detect context)
    # Safer: find "Fross Garage Band" as KEY (followed by :) and check it's followed by { or "
    # Only restore when it's a KEY (repo name), not a value
    # The original key was "YARG" inside Repos: { "YARG": { "Name": ... } }

    # Fix: "Fross Garage Band": { → "YARG": {  (only when value is object - repo entry)
    raw = re.sub(
        r'"Fross Garage Band"(\s*:\s*\{)',
        r'"YARG"\1',
        raw
    )

    if raw != original:
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(raw)
        n = len(re.findall(r'"YARG"\s*:\s*\{', raw))
        print(f"  ✓ {fname}: chave YARG restaurada ({n} vez)")
        fixed += 1
    else:
        print(f"  - {fname}: sem mudança")

print(f"\n  Total: {fixed} arquivo(s) corrigido(s)")
PYEOF

# ── 4. Verificar Fross Garage Band.app launcher ────────
echo ""
echo "[ 4/4 ] Verificando Fross Garage Band.app launcher..."
LAUNCHER="/Applications/Fross Garage Band.app"
if [ -d "$LAUNCHER" ]; then
    echo "  ✓ Fross Garage Band.app existe"
    EXEC="$LAUNCHER/Contents/MacOS/FrossGarageBand"
    if [ -f "$EXEC" ]; then
        echo "  ✓ Executável existe"
        echo ""
        echo "  Script do launcher:"
        cat "$EXEC" | sed 's/^/    /'
    fi
else
    echo "  ✗ Fross Garage Band.app NÃO existe!"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "IMPORTANTE: Para BepInEx funcionar, o jogo DEVE ser"
echo "lançado via 'Fross Garage Band' (não YARG.app direto)."
echo "O plugin intercepta o botão Credits para abrir o Download Music."
echo ""
read -p "Pressione Enter para fechar..."
