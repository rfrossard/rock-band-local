#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Fross Garage Band — Download Music via Credits.json
#
#  Abordagem segura: zero modificação no DLL.
#  Substitui apenas o conteúdo do Credits.json e atualiza
#  os lang JSONs para mostrar "Download Music" como título.
#
#  O que faz:
#    1. Backup de Credits.json (só na primeira vez)
#    2. Substitui Credits.json com catálogo Rhythmverse
#    3. Ajusta header "Contributors" → "📥 Download Music"
#       em todos os lang JSONs
#
#  Para reverter: execute restore_yarg.command
# ══════════════════════════════════════════════════════════════
cd "$(dirname "$0")"

STREAMING="/Applications/YARG.app/Contents/Resources/Data/StreamingAssets"
CREDITS="$STREAMING/Credits.json"
LANG_DIR="$STREAMING/lang"

echo "══════════════════════════════════════════════════════"
echo "  Fross Garage Band — Patch Download Music"
echo "══════════════════════════════════════════════════════"
echo ""

if [ ! -d "$STREAMING" ]; then
    echo "  ✗ YARG não encontrado em /Applications/YARG.app"
    read -p "Enter para fechar..."; exit 1
fi

# ── 1. Credits.json ───────────────────────────────────────────
echo "[ 1/2 ] Substituindo Credits.json..."

python3 - << 'PYEOF'
import json, os, shutil

CREDITS = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/Credits.json"
BAK = CREDITS + ".bak_original"

# Backup só na primeira execução
if not os.path.exists(BAK) and os.path.exists(CREDITS):
    shutil.copy2(CREDITS, BAK)
    print(f"  ✓ Backup original criado")

catalog = [
    # Seção de destaque (SpecialRole "ProjectManager" → aparece na primeira seção)
    # O header será renomeado para "📥 Download Music" via lang JSON
    {
        "Name": "🎸  Fross Garage Band — Download Music",
        "SpecialRole": "ProjectManager",
        "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg"},
        "Contributions": {}
    },

    # Artistas / coleções — SpecialRole "ProjectManager" = primeira seção
    {"Name": "Green Day — Coleção Completa",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=green+day"},
     "Contributions": {}},

    {"Name": "Metallica — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=metallica"},
     "Contributions": {}},

    {"Name": "Red Hot Chili Peppers",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=red+hot+chili+peppers"},
     "Contributions": {}},

    {"Name": "Nirvana — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=nirvana"},
     "Contributions": {}},

    {"Name": "Foo Fighters — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=foo+fighters"},
     "Contributions": {}},

    {"Name": "Pearl Jam — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=pearl+jam"},
     "Contributions": {}},

    {"Name": "Soundgarden — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=soundgarden"},
     "Contributions": {}},

    {"Name": "Alice in Chains — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=alice+in+chains"},
     "Contributions": {}},

    {"Name": "Iron Maiden — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=iron+maiden"},
     "Contributions": {}},

    {"Name": "Black Sabbath / Ozzy",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=black+sabbath"},
     "Contributions": {}},

    {"Name": "Guns N' Roses — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=guns+n+roses"},
     "Contributions": {}},

    {"Name": "AC/DC — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=acdc"},
     "Contributions": {}},

    {"Name": "Aerosmith — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=aerosmith"},
     "Contributions": {}},

    {"Name": "Rage Against the Machine",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=rage+against+the+machine"},
     "Contributions": {}},

    {"Name": "Audioslave — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=audioslave"},
     "Contributions": {}},

    {"Name": "System of a Down",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=system+of+a+down"},
     "Contributions": {}},

    {"Name": "Pantera — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=pantera"},
     "Contributions": {}},

    {"Name": "Slayer — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=slayer"},
     "Contributions": {}},

    {"Name": "DragonForce — Through the Fire + mais",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=dragonforce"},
     "Contributions": {}},

    {"Name": "Legião Urbana — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=legiao+urbana"},
     "Contributions": {}},

    {"Name": "Sepultura — Discografia",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=sepultura"},
     "Contributions": {}},

    {"Name": "PixelBeat — Trilhas de Video Game",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=pixelbeat"},
     "Contributions": {}},

    {"Name": "J-Rock Band Project",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=j-rock"},
     "Contributions": {}},

    {"Name": "Rock Brasileiro — Seleção Completa",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=brasileiro"},
     "Contributions": {}},

    # Busca livre por gênero
    {"Name": "🔍  Buscar: Metal",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=metal"},
     "Contributions": {}},

    {"Name": "🔍  Buscar: Punk / Hardcore",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=punk"},
     "Contributions": {}},

    {"Name": "🔍  Buscar: Classic Rock",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=classic+rock"},
     "Contributions": {}},

    {"Name": "🔍  Buscar: Pop",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg?query=pop"},
     "Contributions": {}},

    {"Name": "🔍  Todas as músicas (Rhythmverse YARG)",
     "SpecialRole": "ProjectManager",
     "Socials": {"Website": "https://rhythmverse.co/songfiles/game/yarg"},
     "Contributions": {}},
]

with open(CREDITS, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)
    f.write('\n')

print(f"  ✓ Credits.json substituído — {len(catalog)} entradas")
print("    Cada entrada tem botão 'Website' que abre o Rhythmverse")
PYEOF

# ── 2. Lang JSONs — renomear header ProjectManager ────────────
echo ""
echo "[ 2/2 ] Atualizando headers nos lang JSONs..."

python3 - << 'PYEOF'
import os, json

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

# ProjectManager header → nosso título de Download Music
PM_VALUES = {
    "en-US":  "📥 Download Music",
    "pt-BR":  "📥 Baixar Músicas",
    "es-ES":  "📥 Descargar Música",
    "es-419": "📥 Descargar Música",
    "fr-FR":  "📥 Télécharger Musique",
    "de-DE":  "📥 Musik Herunterladen",
    "it-IT":  "📥 Scarica Musica",
    "ja-JP":  "📥 音楽をダウンロード",
    "ko-KR":  "📥 음악 다운로드",
    "zh-CN":  "📥 下载音乐",
    "zh-TW":  "📥 下載音樂",
    "nl-NL":  "📥 Muziek Downloaden",
    "pl-PL":  "📥 Pobierz Muzykę",
    "ru-RU":  "📥 Скачать Музыку",
    "tr-TR":  "📥 Müzik İndir",
}
DEFAULT_PM = "📥 Download Music"

patched = 0
for fname in sorted(os.listdir(LANG_DIR)):
    if not fname.endswith('.json'): continue
    path = os.path.join(LANG_DIR, fname)
    try:
        with open(path, encoding='utf-8-sig') as f:
            data = json.load(f)
        header = data["Menu"]["Credits"]["Header"]
        locale = fname.replace('.json', '')
        val = PM_VALUES.get(locale, DEFAULT_PM)
        changed = False
        if header.get("ProjectManager") != val:
            header["ProjectManager"] = val
            changed = True
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')
            patched += 1
            print(f"  ✓ {fname} → ProjectManager = \"{val}\"")
        else:
            print(f"  — {fname} (sem alteração)")
    except (KeyError, TypeError):
        print(f"  ⚠ {fname}: Menu.Credits.Header não encontrado")
    except Exception as e:
        print(f"  ✗ {fname}: {e}")

print(f"\n  Total: {patched} arquivo(s) atualizado(s)")
PYEOF

echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✅  Patch concluído! (sem tocar no DLL)"
echo ""
echo "  O que foi feito:"
echo "    ✓ Credits.json → catálogo com 30 coleções Rhythmverse"
echo "    ✓ Header 'Download Music' nos lang JSONs"
echo ""
echo "  Abra Fross Garage Band → clique 'Download Music'"
echo "  Cada item tem botão 'Website' que abre o Rhythmverse"
echo "  com busca pré-filtrada para aquela coleção."
echo ""
echo "  Para busca completa com filtros avançados:"
echo "    python3 main.py  (Rock Band Local)"
echo "    → clique '📥 Download Music' no menu"
echo "══════════════════════════════════════════════════════"
echo ""
read -p "Pressione Enter para fechar..."
