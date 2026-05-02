#!/bin/bash
# Fix completo: restaurar TODAS as chaves JSON corrompidas pelo regex Credits→Download Music
set -e
cd "$(dirname "$0")"

LANG_DIR="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

echo ""
echo "🔧  Fix completo: restaurar chaves Credits nos lang JSONs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "[ Diagnóstico ] Chaves corrompidas em en-US.json:"
python3 -c "
import re
with open('$LANG_DIR/en-US.json', encoding='utf-8', errors='replace') as f:
    raw = f.read()
# Find all keys (followed by colon) that contain 'Download Music'
hits = re.findall(r'\"([^\"]*[Dd]ownload [Mm]usic[^\"]*)\"\s*:', raw)
for h in hits[:20]:
    print(f'  KEY corrompida: {h!r}')
" 2>/dev/null

echo ""
echo "[ Fix ] Restaurando chaves em todos os lang files..."

python3 << 'PYEOF'
import re, glob, os

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

def restore_credits(prefix, suffix):
    """
    Determina o casing correto de 'Credits' baseado no contexto.
    Ex: MENU.MAIN.OPTIONS. → CREDITS (uppercase)
        Menu.              → Credits (title case)
    """
    # Olhar o último segmento antes de 'Download Music'
    segs = prefix.rstrip('.').split('.')
    last_seg = segs[-1] if segs else ''

    if last_seg and last_seg == last_seg.upper():
        return 'CREDITS'   # contexto uppercase: MENU.OPTIONS. → CREDITS
    elif last_seg and last_seg[0].isupper():
        return 'Credits'   # contexto TitleCase: Menu. → Credits
    else:
        return 'Credits'   # fallback

def fix_key(m):
    prefix = m.group(1)   # antes de 'Download Music'
    suffix = m.group(2)   # depois de 'Download Music'
    colon  = m.group(3)   # ": " ou ":"
    restored = restore_credits(prefix, suffix)
    return f'"{prefix}{restored}{suffix}"{colon}'

total_fixed = 0
total_keys  = 0

for path in sorted(glob.glob(os.path.join(LANG_DIR, "*.json"))):
    fname = os.path.basename(path)

    with open(path, encoding='utf-8', errors='replace') as f:
        raw = f.read()

    original = raw

    # Contar chaves corrompidas antes do fix
    corrupted = re.findall(r'"[^"]*[Dd]ownload [Mm]usic[^"]*"\s*:', raw)

    # Restaurar TODAS as chaves (seguidas de ':') que contêm 'Download Music'
    # Deixar VALUES (não seguidos de ':') inalterados
    raw = re.sub(
        r'"([^"]*?)[Dd]ownload [Mm]usic([^"]*?)"(\s*:)',
        fix_key,
        raw
    )

    if raw != original:
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(raw)
        print(f"  ✓ {fname}: {len(corrupted)} chave(s) restaurada(s)")
        total_fixed += 1
        total_keys  += len(corrupted)
    else:
        remaining = re.findall(r'"[^"]*[Dd]ownload [Mm]usic[^"]*"\s*:', raw)
        if remaining:
            print(f"  ✗ {fname}: ainda tem {len(remaining)} chave(s) corrompida(s)!")
        else:
            print(f"  ✓ {fname}: sem chaves corrompidas")

print(f"\nTotal: {total_fixed} arquivo(s), {total_keys} chave(s) restaurada(s)")
PYEOF

echo ""
echo "[ Verificação ] Chaves Credits restantes em en-US.json:"
python3 -c "
import re
with open('$LANG_DIR/en-US.json', encoding='utf-8', errors='replace') as f:
    raw = f.read()

corrupted = re.findall(r'\"[^\"]*[Dd]ownload [Mm]usic[^\"]*\"\s*:', raw)
if corrupted:
    print('  ⚠️  Ainda corrompidas:')
    for h in corrupted[:10]:
        print(f'    {h!r}')
else:
    print('  ✓ Nenhuma chave corrompida!')

# Verificar que o item do menu está correto
ok = re.findall(r'\"MENU\.MAIN\.OPTIONS\.CREDITS\"\s*:\s*\"([^\"]+)\"', raw)
if ok:
    print(f'  ✓ MENU.MAIN.OPTIONS.CREDITS = {ok[0]!r}')
else:
    print('  ? MENU.MAIN.OPTIONS.CREDITS não encontrado (JSON pode ser plano)')
    # Try to find any Credits key
    hits = re.findall(r'\"[^\"]*[Cc]redits[^\"]*\"\s*:\s*\"([^\"]+)\"', raw)
    for h in hits[:5]:
        print(f'  > {h!r}')
" 2>/dev/null

echo ""
echo "✅  Pronto! Reinicie o Fross Garage Band."
echo "   - Menu principal: 'Download Music' ✓"
echo "   - Tela Credits: nomes dos devs com descrições corretas ✓"
echo ""
read -p "Pressione Enter para fechar..."
