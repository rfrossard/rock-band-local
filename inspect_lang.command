#!/bin/bash
# Inspecionar estrutura real do lang JSON para entender o formato
cd "$(dirname "$0")"
LANG_DIR="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

echo ""
echo "🔍  Inspecionar en-US.json — estrutura de chaves"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << 'PYEOF'
import re

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"
path = f"{LANG_DIR}/en-US.json"

with open(path, encoding='utf-8', errors='replace') as f:
    raw = f.read()

# ── 1. Find ALL JSON keys (anything before ": ")
# Match: "key": value  pattern
all_keys = re.findall(r'"([^"\n]{1,120})"\s*:', raw)
print(f"Total de chaves: {len(all_keys)}")
print()

# ── 2. Show first 5 keys to understand the format
print("Primeiras 10 chaves:")
for k in all_keys[:10]:
    print(f"  {k!r}")
print()

# ── 3. Find any key containing "credits", "CREDITS", "Credits", "Download", "Music"
print("Chaves contendo 'credits' ou 'Download' (case-insensitive):")
problem_keys = [k for k in all_keys if re.search(r'credit|download|music', k, re.IGNORECASE)]
for k in problem_keys[:30]:
    # Find its value too
    val_match = re.search(re.escape(f'"{k}"') + r'\s*:\s*("(?:[^"\\]|\\.)*"|\{|\[)', raw)
    if val_match:
        val_preview = val_match.group(1)[:60]
        print(f"  KEY: {k!r}  →  {val_preview!r}")
    else:
        print(f"  KEY: {k!r}")
print()

# ── 4. Show context around MENU keys to understand nesting
print("Chaves MENU (primeiras 15):")
menu_keys = [k for k in all_keys if k.startswith('MENU') or k.startswith('Menu')]
for k in menu_keys[:15]:
    print(f"  {k!r}")
PYEOF

echo ""
read -p "Pressione Enter para fechar..."
