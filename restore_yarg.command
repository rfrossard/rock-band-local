#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Fross Garage Band — Restaurar YARG ao estado original
#  Restaura Assembly-CSharp.dll do backup e valida lang JSONs.
#  Execute este script se o jogo apresentar regressões.
# ══════════════════════════════════════════════════════════════
cd "$(dirname "$0")"

YARG="/Applications/YARG.app"
MANAGED="$YARG/Contents/Resources/Data/Managed"
DLL="$MANAGED/Assembly-CSharp.dll"
LANG_DIR="$YARG/Contents/Resources/Data/StreamingAssets/lang"
STREAMING="$YARG/Contents/Resources/Data/StreamingAssets"

echo "══════════════════════════════════════════════════════"
echo "  Fross Garage Band — Restore YARG"
echo "══════════════════════════════════════════════════════"
echo ""

if [ ! -d "$YARG" ]; then
    echo "  ✗ YARG.app não encontrado em /Applications"
    read -p "Enter para fechar..."; exit 1
fi

# ── 1. Restaurar Assembly-CSharp.dll ─────────────────────────
echo "[ 1/3 ] Verificando Assembly-CSharp.dll..."

DLL_RESTORED=0
for bak in "$DLL.bak_dm" "$DLL.bak_original" "$DLL.bak"; do
    if [ -f "$bak" ]; then
        echo "  Backup encontrado: $bak"
        cp "$bak" "$DLL"
        codesign --remove-signature "$DLL" 2>/dev/null || true
        codesign -s - "$DLL" 2>/dev/null || true
        DLL_RESTORED=1
        echo "  ✓ DLL restaurado do backup"
        break
    fi
done

if [ $DLL_RESTORED -eq 0 ]; then
    echo "  — Nenhum backup encontrado (DLL nunca foi patchado — ok)"
fi

# Verificar tamanho do DLL (sanity check: original ~1.3MB)
if [ -f "$DLL" ]; then
    SIZE=$(wc -c < "$DLL")
    if [ "$SIZE" -lt 500000 ]; then
        echo "  ⚠ DLL parece corrompido (${SIZE} bytes — esperado >1MB)"
    else
        echo "  ✓ DLL ok ($(echo "$SIZE/1024" | bc) KB)"
    fi
fi

# ── 2. Validar e corrigir lang JSONs ─────────────────────────
echo ""
echo "[ 2/3 ] Validando lang JSONs..."

python3 - << 'PYEOF'
import os, json, sys

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

if not os.path.isdir(LANG_DIR):
    print("  ✗ Pasta lang não encontrada")
    sys.exit(0)

errors = []
for fname in sorted(os.listdir(LANG_DIR)):
    if not fname.endswith('.json'): continue
    path = os.path.join(LANG_DIR, fname)
    try:
        with open(path, encoding='utf-8-sig') as f:
            data = json.load(f)
        # Verificar chave crítica que causa crash se ausente
        # Menu.Credits.Repos.YARG deve existir como chave "YARG"
        try:
            repos = data["Menu"]["Credits"]["Repos"]
            if "Fross Garage Band" in repos and "YARG" not in repos:
                # Fix: renomear a chave corrompida
                repos["YARG"] = repos.pop("Fross Garage Band")
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.write('\n')
                print(f"  🔧 {fname}: chave YARG restaurada em Credits.Repos")
            else:
                print(f"  ✓ {fname}")
        except (KeyError, TypeError):
            print(f"  ✓ {fname} (sem Credits.Repos — ok)")
    except json.JSONDecodeError as e:
        print(f"  ✗ {fname}: JSON INVÁLIDO — {e}")
        errors.append(fname)
    except Exception as e:
        print(f"  ✗ {fname}: erro — {e}")
        errors.append(fname)

if errors:
    print(f"\n  ⚠ {len(errors)} arquivo(s) com problema. Verifique manualmente.")
else:
    print(f"\n  ✓ Todos os lang JSONs são válidos.")
PYEOF

# ── 3. Verificar Credits.json ─────────────────────────────────
echo ""
echo "[ 3/3 ] Verificando Credits.json..."

python3 - << 'PYEOF'
import os, json

CREDITS = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/Credits.json"
BAK_ORIG = CREDITS + ".bak_original"

# Se existe backup do original, restaurar
if os.path.exists(BAK_ORIG):
    import shutil
    shutil.copy2(BAK_ORIG, CREDITS)
    print("  ✓ Credits.json restaurado do backup original")
elif os.path.exists(CREDITS):
    try:
        with open(CREDITS, encoding='utf-8') as f:
            data = json.load(f)
        # Checar se parece nosso catálogo (tem "Rhythmverse") ou original YARG
        sample = str(data[:1]) if isinstance(data, list) and data else ""
        if "Rhythmverse" in sample or "rhythmverse.co" in str(data[:2]):
            print("  ℹ Credits.json tem nosso catálogo (Download Music)")
        else:
            print("  ✓ Credits.json parece original do YARG")
    except Exception as e:
        print(f"  ✗ Erro ao verificar Credits.json: {e}")
else:
    print("  ✗ Credits.json não encontrado!")

PYEOF

echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✅  Restore concluído!"
echo ""
echo "  Agora teste o jogo:"
echo "    1. Abra /Applications/YARG.app normalmente"
echo "    2. Verifique se a biblioteca de músicas carrega"
echo "    3. Se funcionar, execute patch_download_music.command"
echo "══════════════════════════════════════════════════════"
echo ""
read -p "Pressione Enter para fechar..."
