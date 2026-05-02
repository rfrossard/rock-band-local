#!/bin/bash
# Diagnose and fix MENU.MAIN.OPTIONS.CREDITS localization key
set -e
cd "$(dirname "$0")"

LANG_DIR="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

echo ""
echo "🔍  Diagnose: MENU.MAIN.OPTIONS.CREDITS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show current value for this key in en-US.json
echo "[ en-US.json ] grep CREDITS / credits / Download:"
python3 << 'PYEOF'
import json, os

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"
f = os.path.join(LANG_DIR, "en-US.json")

try:
    with open(f) as fh:
        raw = fh.read()
    data = json.loads(raw)
except Exception as e:
    print(f"ERROR loading JSON: {e}")
    # Show raw around CREDITS
    import re
    hits = re.findall(r'.{0,60}(?:CREDITS|credits|Credits|Download|Music).{0,60}', raw, re.IGNORECASE)
    for h in hits[:10]:
        print(repr(h))
    exit()

# Find CREDITS key(s)
found = False
for k, v in data.items():
    if 'CREDITS' in k.upper() or 'CREDIT' in k.upper():
        print(f"  KEY: {k!r}  →  VALUE: {v!r}")
        found = True

if not found:
    print("  No CREDITS key found — scanning for 'Download Music':")
    for k, v in data.items():
        if isinstance(v, str) and 'download' in v.lower():
            print(f"  KEY: {k!r}  →  VALUE: {v!r}")
PYEOF

echo ""
echo "[ Fix ] Setting MENU.MAIN.OPTIONS.CREDITS = 'Download Music' in all lang files..."
python3 << 'PYEOF'
import json, os, glob

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

TARGET_KEY = "MENU.MAIN.OPTIONS.CREDITS"
TARGET_VAL = "Download Music"

fixed = 0
for path in sorted(glob.glob(os.path.join(LANG_DIR, "*.json"))):
    fname = os.path.basename(path)
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:
        print(f"  ✗ {fname}: JSON error — {e}")
        continue

    changed = False
    # Try exact key first
    if TARGET_KEY in data:
        if data[TARGET_KEY] != TARGET_VAL:
            print(f"  {fname}: '{data[TARGET_KEY]}' → '{TARGET_VAL}'")
            data[TARGET_KEY] = TARGET_VAL
            changed = True
        else:
            print(f"  {fname}: already '{TARGET_VAL}' ✓")
    else:
        # Key missing — add it
        data[TARGET_KEY] = TARGET_VAL
        print(f"  {fname}: key missing — added '{TARGET_VAL}'")
        changed = True

    if changed:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        fixed += 1

print(f"\nTotal: {fixed} arquivo(s) atualizado(s)")
PYEOF

echo ""
echo "✅  Feito! Reinicie o Fross Garage Band para ver 'Download Music' no menu."
echo ""
read -p "Pressione Enter para fechar..."
