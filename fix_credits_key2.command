#!/bin/bash
# Fix: restore Credits KEY in lang JSONs (regex corrupted both key and value)
set -e
cd "$(dirname "$0")"

LANG_DIR="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

echo ""
echo "🔧  Fix: restaurar chave Credits nos lang JSONs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show raw context around the problem
echo "[ Diagnóstico ] Conteúdo atual em en-US.json:"
python3 -c "
import re
with open('$LANG_DIR/en-US.json', encoding='utf-8', errors='replace') as f:
    raw = f.read()
# Find all occurrences of Download Music as a KEY
hits = re.findall(r'.{0,40}\"Download Music\"\s*:.{0,60}', raw)
for h in hits[:10]:
    print(' ', repr(h))
" 2>/dev/null || grep -o '"Download Music"[^,}]*' "$LANG_DIR/en-US.json" | head -10

echo ""
echo "[ Fix ] Aplicando correção em todos os lang files..."

python3 << 'PYEOF'
import os, re, glob

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

fixed_files = 0

for path in sorted(glob.glob(os.path.join(LANG_DIR, "*.json"))):
    fname = os.path.basename(path)

    with open(path, encoding='utf-8', errors='replace') as f:
        raw = f.read()

    original = raw

    # Problem: regex replaced "Credits": "Credits" → "Download Music": "Download Music"
    # (both key and value were changed because regex hit both)
    # Fix A: "Download Music": "Download Music" → "Credits": "Download Music"
    # (restore the key, keep the value)
    raw_new = re.sub(
        r'"Download Music"(\s*:\s*)"Download Music"',
        r'"Credits"\1"Download Music"',
        raw
    )

    # Fix B: also handle title-case / uppercase variants that may have been left
    # e.g. "download music": "Download Music" (in case of case-insensitive replacement)
    raw_new = re.sub(
        r'"[Dd]ownload [Mm]usic"(\s*:\s*)"Download Music"',
        r'"Credits"\1"Download Music"',
        raw_new
    )

    if raw_new != original:
        # Write with same encoding, preserving original characters
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(raw_new)

        # Count how many replacements
        n = len(re.findall(r'"Credits"\s*:\s*"Download Music"', raw_new))
        print(f"  ✓ {fname}: chave restaurada ({n} ocorrência(s))")
        fixed_files += 1
    else:
        # Check if key already correct
        if '"Credits"' in raw and '"Download Music"' in raw:
            print(f"  ✓ {fname}: já parece correto")
        else:
            print(f"  ? {fname}: sem mudança (verifique manualmente)")

print(f"\nTotal: {fixed_files} arquivo(s) corrigido(s)")
PYEOF

echo ""

# Show final state
echo "[ Verificação ] Chaves Credits no en-US.json após fix:"
python3 -c "
import re
with open('$LANG_DIR/en-US.json', encoding='utf-8', errors='replace') as f:
    raw = f.read()
hits = re.findall(r'.{0,30}\"Credits\"\s*:.{0,50}', raw)
for h in hits[:10]:
    print(' ', repr(h))
" 2>/dev/null

echo ""
echo "✅  Pronto! Reinicie o Fross Garage Band."
echo "   O menu deve mostrar 'Download Music' em vez do código."
echo ""
read -p "Pressione Enter para fechar..."
