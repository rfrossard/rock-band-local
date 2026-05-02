#!/bin/bash
cd "$(dirname "$0")"
LANG_DIR="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

echo ""
echo "🔍  Deep inspect: todas ocorrências de Credits em en-US.json"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << 'PYEOF'
import re

path = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang/en-US.json"
with open(path, encoding='utf-8', errors='replace') as f:
    raw = f.read()

print("=== Todas ocorrências de 'Credits' (com contexto) ===\n")
for i, m in enumerate(re.finditer(r'"Credits"', raw), 1):
    start = max(0, m.start() - 60)
    end   = min(len(raw), m.end() + 100)
    snippet = raw[start:end]
    # Clean up for display
    snippet = snippet.replace('\n', '↵').replace('\r', '')
    print(f"[{i}] pos={m.start():5d}: ...{snippet}...\n")

print("=== Ocorrências de 'Download Music' como KEY (seguido de :) ===\n")
for i, m in enumerate(re.finditer(r'"[Dd]ownload [Mm]usic"\s*:', raw), 1):
    start = max(0, m.start() - 60)
    end   = min(len(raw), m.end() + 100)
    snippet = raw[start:end].replace('\n', '↵').replace('\r', '')
    print(f"[{i}] pos={m.start():5d}: ...{snippet}...\n")

if not list(re.finditer(r'"[Dd]ownload [Mm]usic"\s*:', raw)):
    print("  ✓ Nenhuma chave 'Download Music' encontrada!\n")

print("=== Ocorrências de 'Download Music' como VALUE ===\n")
for i, m in enumerate(re.finditer(r':\s*"[Dd]ownload [Mm]usic"', raw), 1):
    start = max(0, m.start() - 80)
    end   = min(len(raw), m.end() + 40)
    snippet = raw[start:end].replace('\n', '↵').replace('\r', '')
    print(f"[{i}] pos={m.start():5d}: ...{snippet}...\n")
PYEOF

echo ""
read -p "Pressione Enter para fechar..."
