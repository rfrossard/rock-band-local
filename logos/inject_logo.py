#!/Users/frossard/Documents/Claude/Projects/Rock Band Local/.venv/bin/python3
"""
inject_logo.py — Fross Garage Band logo injector for YARG
==========================================================
Reads the PNG files in this folder and replaces the matching
textures inside YARG's Unity asset bundles.

Usage (any of these work):
    Double-click  "Run Injector.command"  in Finder   ← easiest
    python3 inject_logo.py                            ← from Terminal
    ./inject_logo.py                                  ← if executable

Re-run any time you update a PNG to see the change in-game.
YARG must be closed while running this script.

PNG files (keep their exact pixel sizes when replacing):
    Logo_White.png       1024 ×  512  – main menu logo
    YARG_Colorless.png    512 ×  512  – small icon / loading logo
    MenuHeader.png       1000 ×  160  – inner song-select header bar
    Splash_Logo.png      1920 × 1080  – splash / boot screen
    Header.png           1920 ×  300  – song-selection screen header
    PauseBackground.png  1920 × 1080  – gameplay pause screen background
"""

import sys, os, shutil, datetime, subprocess

# ── Use the project venv Python directly (avoids ABI/version mismatches). ─
# If this script is being run by the wrong interpreter, re-exec with the
# venv Python and exit.  This is transparent to the user.
_HERE    = os.path.dirname(os.path.abspath(__file__))
_VENV_PY = os.path.normpath(os.path.join(_HERE, '..', '.venv', 'bin', 'python3'))

if not os.path.isfile(_VENV_PY):
    print("ERROR: Project venv not found.")
    print(f"       Expected: {_VENV_PY}")
    print("       Set up the venv first:  cd .. && python3 -m venv .venv && .venv/bin/pip install UnityPy Pillow")
    sys.exit(1)

# If running under the wrong interpreter, re-launch with the venv Python.
# Use realpath only for the equality check (to handle symlink chains) but
# pass the symlink path to subprocess so the venv's site-packages activate.
if os.path.realpath(sys.executable) != os.path.realpath(_VENV_PY):
    result = subprocess.run([_VENV_PY] + sys.argv)
    sys.exit(result.returncode)

SCRIPT_DIR  = _HERE
YARG_DATA   = "/Applications/YARG.app/Contents/Resources/Data"
ASSETS1     = os.path.join(YARG_DATA, "sharedassets1.assets")
ASSETS0     = os.path.join(YARG_DATA, "sharedassets0.assets")

ASSETS2 = os.path.join(YARG_DATA, "sharedassets2.assets")

REPLACEMENTS = {
    # texture_name_in_unity  : (png_filename,            assets_file)
    # ── main menu / splash ──────────────────────────────────────────
    "Logo_White":             ("Logo_White.png",          ASSETS1),
    "YARG_Colorless":         ("YARG_Colorless.png",      ASSETS1),
    "MenuHeader":             ("MenuHeader.png",          ASSETS1),
    "Splash_Logo":            ("Splash_Logo.png",         ASSETS0),
    # ── song-selection screen ────────────────────────────────────────
    "Header":                 ("Header.png",              ASSETS0),
    # ── gameplay / pause screen ──────────────────────────────────────
    "PauseBackground":        ("PauseBackground.png",     ASSETS2),
}

def backup(path):
    bak = path + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print(f"  backed up → {os.path.basename(bak)}")
    else:
        print(f"  backup already exists, skipping")

def inject(assets_path, replacements_for_file):
    try:
        import UnityPy
    except ImportError:
        print("ERROR: UnityPy not found. Install with:  pip3 install UnityPy")
        sys.exit(1)
    from PIL import Image

    env = UnityPy.load(assets_path)
    replaced = []

    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", "")
        if name not in replacements_for_file:
            continue

        png_path = replacements_for_file[name]
        if not os.path.exists(png_path):
            print(f"  ⚠  {name}: PNG not found at {png_path}, skipping")
            continue

        w = getattr(data, "m_Width",  0)
        h = getattr(data, "m_Height", 0)
        img = Image.open(png_path).convert("RGBA")

        if img.size != (w, h):
            print(f"  ℹ  {name}: resizing {img.size} → ({w}, {h})")
            img = img.resize((w, h), Image.LANCZOS)

        data.image = img
        data.save()
        replaced.append(name)
        print(f"  ✓  {name}  ({w}×{h})")

    if not replaced:
        print(f"  ⚠  No matching textures found in {os.path.basename(assets_path)}")
        return

    raw = env.file.save()
    with open(assets_path, "wb") as f:
        f.write(raw)
    print(f"  → wrote {len(raw):,} bytes to {os.path.basename(assets_path)}")

# ── Localization patcher ───────────────────────────────────────────────────────

LANG_DIR = os.path.join("/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang")

MOTD_EN = (
    '<align=center><size=32><b>Welcome to Fross Garage Band!</b></size></align>'
    '\\n\\nv0.14 brings 5 Lane Keys, a new MIDI Drums profile type, easier instrument setup, '
    '3D venue events, performance improvements, many visual improvements, and more.'
    '\\n\\n<b>Download new songs via the Rock Band Local app — Rhythmverse integration included.</b>'
    '\\n\\nRock on!'
)
MOTD_PT = (
    '<align=center><size=32><b>Bem-vindo ao Fross Garage Band!</b></size></align>'
    '\\n\\nv0.14 traz 5 Teclas Lane, novo perfil de MIDI Drums, configuração de instrumentos '
    'mais fácil, eventos de palco 3D, melhorias de performance e muito mais.'
    '\\n\\n<b>Baixe novas músicas pelo app Rock Band Local — integração Rhythmverse inclusa.</b>'
    '\\n\\nBora tocar!'
)

def _patch_lang():
    import re
    if not os.path.isdir(LANG_DIR):
        print("  ⚠  Lang dir not found, skipping")
        return
    for fname in os.listdir(LANG_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(LANG_DIR, fname)
        with open(path, encoding='utf-8-sig') as f:
            content = f.read()
        orig = content
        motd = MOTD_PT if fname.startswith('pt-') else MOTD_EN
        content = re.sub(
            r'"MessageOfTheDay"\s*:\s*"(?:[^"\\]|\\.)*"',
            f'"MessageOfTheDay": "{motd}"',
            content
        )
        content = re.sub(
            r'("Credits"\s*:\s*")[^"]{2,40}(")',
            r'\1Download Music\2',
            content
        )
        if content != orig:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓  lang/{fname}")

# ── main ─────────────────────────────────────────────────────────────────────

print("=" * 58)
print("  Fross Garage Band — YARG Logo Injector")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 58)

# Check YARG is not running
result = subprocess.run(["pgrep", "-x", "YARG"], capture_output=True)
if result.returncode == 0:
    print("\nERROR: YARG is currently running. Please close it first.")
    sys.exit(1)

# Group replacements by assets file
by_file = {}
for tex_name, (png_file, assets_file) in REPLACEMENTS.items():
    png_path = os.path.join(SCRIPT_DIR, png_file)
    by_file.setdefault(assets_file, {})[tex_name] = png_path

for assets_path, rep in by_file.items():
    print(f"\n[ {os.path.basename(assets_path)} ]")
    if not os.path.exists(assets_path):
        print(f"  ⚠  Not found: {assets_path}")
        continue
    backup(assets_path)
    inject(assets_path, rep)

print("\nInjecting localization patches...")
_patch_lang()

print("\nDone! Launch YARG to see the new logo and branding.")
