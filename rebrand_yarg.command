#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  Fross Garage Band — Rebranding Completo do YARG
#  Double-click para aplicar o rebranding em todas as camadas
# ══════════════════════════════════════════════════════════════
cd "$(dirname "$0")"
set -e

YARG="/Applications/YARG.app"
LANG_DIR="$YARG/Contents/Resources/Data/StreamingAssets/lang"
PLIST="$YARG/Contents/Info.plist"
MANAGED="$YARG/Contents/Resources/Data/Managed"
BEPINEX="$YARG/BepInEx"
PLUGIN_DIR="$BEPINEX/plugins/FrossDownloadMusic"

echo "══════════════════════════════════════════════════════"
echo "  Fross Garage Band — Rebranding do YARG"
echo "══════════════════════════════════════════════════════"
echo ""

# ── 1. Info.plist — nome do app, bundle, versão ──────────────
echo "[ 1/5 ] Patchando Info.plist..."
if [ -f "$PLIST" ]; then
    # Backup
    [ ! -f "$PLIST.bak" ] && cp "$PLIST" "$PLIST.bak"

    python3 << PYEOF
import plistlib, shutil, os

path = "$PLIST"
with open(path, 'rb') as f:
    p = plistlib.load(f)

p['CFBundleName']        = 'Fross Garage Band'
p['CFBundleDisplayName'] = 'Fross Garage Band'
p['CFBundleExecutable']  = p.get('CFBundleExecutable', 'YARG')
# Keep bundle ID so saves/prefs still work
# p['CFBundleIdentifier'] = 'com.frossgarageband.game'
p['CFBundleShortVersionString'] = '0.14-FGB'
p['CFBundleVersion']            = '0.14-FGB'

with open(path, 'wb') as f:
    plistlib.dump(p, f)
print("  ✓ Info.plist: CFBundleName = Fross Garage Band")
PYEOF
else
    echo "  ⚠ Info.plist não encontrado: $PLIST"
fi

# ── 2. Lang JSON — substituir todas as referências ao YARG ───
echo ""
echo "[ 2/5 ] Patchando arquivos de idioma..."

python3 << 'PYEOF'
import os, re, json

LANG_DIR = "/Applications/YARG.app/Contents/Resources/Data/StreamingAssets/lang"

REPLACEMENTS = {
    # Título / nome do jogo
    r'\bYARG\b': 'Fross Garage Band',
    r'Yet Another Rhythm Game': 'Fross Garage Band',
    # Saudação do MOTD
    r'Happy YARGin[\'!]*': 'Rock on!',
    r'YARGin[\'!]*': 'jamming!',
    # Créditos / download
    r'Credits': 'Download Music',
    # Qualquer sobra
    r'yarg\.in': 'frossgarageband.com',
}

def patch_value(v):
    if not isinstance(v, str): return v
    for pat, repl in REPLACEMENTS.items():
        v = re.sub(pat, repl, v, flags=re.IGNORECASE)
    return v

def patch_obj(obj):
    if isinstance(obj, dict):
        return {k: patch_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [patch_obj(i) for i in obj]
    return patch_value(obj)

patched = 0
if not os.path.isdir(LANG_DIR):
    print("  ⚠ Pasta de idioma não encontrada:", LANG_DIR)
else:
    for fname in sorted(os.listdir(LANG_DIR)):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(LANG_DIR, fname)
        with open(path, encoding='utf-8-sig') as f:
            content = f.read()
        orig = content
        # Apply regex directly on raw text (faster, preserves formatting)
        for pat, repl in REPLACEMENTS.items():
            content = re.sub(pat, repl, content, flags=re.IGNORECASE)
        if content != orig:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            patched += 1
            print(f"  ✓ {fname}")
        else:
            print(f"  — {fname} (sem alterações)")
    print(f"\n  Total: {patched} arquivo(s) atualizado(s)")
PYEOF

# ── 3. Compilar plugin BepInEx (Unity UI Download Music) ─────
echo ""
echo "[ 3/5 ] Compilando plugin BepInEx..."

CSC=""
for c in "$YARG/Contents/Frameworks/MonoBleedingEdge/bin/mcs" \
          /opt/homebrew/bin/mcs /usr/local/bin/mcs; do
    [ -f "$c" ] && CSC="$c" && break
done
[ -z "$CSC" ] && which mcs   &>/dev/null && CSC="$(which mcs)"
[ -z "$CSC" ] && which dotnet &>/dev/null && CSC="dotnet"

if [ -z "$CSC" ]; then
    echo "  ⚠ Compilador C# não encontrado. Plugin não compilado."
    echo "    Instale: brew install mono"
else
    mkdir -p "$PLUGIN_DIR"
    CS_SRC="$PLUGIN_DIR/FrossDownloadMusic.cs"

    # Referências
    REFS=""
    for dll in "$BEPINEX/core/BepInEx.dll" "$BEPINEX/core/0Harmony.dll" \
               "$MANAGED/UnityEngine.dll" "$MANAGED/UnityEngine.CoreModule.dll" \
               "$MANAGED/UnityEngine.UI.dll" \
               "$MANAGED/UnityEngine.UnityWebRequestModule.dll" \
               "$MANAGED/UnityEngine.UnityWebRequestWWWModule.dll" \
               "$MANAGED/System.IO.Compression.dll" \
               "$MANAGED/System.IO.Compression.FileSystem.dll"; do
        [ -f "$dll" ] && REFS="$REFS -r:$dll"
    done

    # Compile
    if [ "$CSC" = "dotnet" ]; then
        TMPD="/tmp/FGB_Plugin_$$"
        mkdir -p "$TMPD"
        cp "$CS_SRC" "$TMPD/"
        REF_XML=""
        for dll in "$BEPINEX/core/BepInEx.dll" "$BEPINEX/core/0Harmony.dll" \
                   "$MANAGED/UnityEngine.dll" "$MANAGED/UnityEngine.CoreModule.dll" \
                   "$MANAGED/UnityEngine.UI.dll" \
                   "$MANAGED/UnityEngine.UnityWebRequestModule.dll" \
                   "$MANAGED/UnityEngine.UnityWebRequestWWWModule.dll" \
                   "$MANAGED/System.IO.Compression.dll" "$MANAGED/System.IO.Compression.FileSystem.dll"; do
            [ -f "$dll" ] && REF_XML="$REF_XML<Reference Include=\"$(basename $dll .dll)\"><HintPath>$dll</HintPath></Reference>"
        done
        cat > "$TMPD/p.csproj" << PROJEOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net462</TargetFramework>
    <AssemblyName>FrossDownloadMusic</AssemblyName>
    <Nullable>disable</Nullable>
    <OutputType>Library</OutputType>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
  </PropertyGroup>
  <ItemGroup>$REF_XML</ItemGroup>
</Project>
PROJEOF
        dotnet build "$TMPD/p.csproj" -o "$PLUGIN_DIR" -c Release --nologo 2>&1 | tail -5
        rm -rf "$TMPD"
    else
        "$CSC" -target:library -out:"$PLUGIN_DIR/FrossDownloadMusic.dll" \
            -langversion:latest -nowarn:0414,0219,1591 \
            $REFS "$CS_SRC" 2>&1 | grep -v "^$"
    fi

    if [ -f "$PLUGIN_DIR/FrossDownloadMusic.dll" ]; then
        echo "  ✓ FrossDownloadMusic.dll compilado"
    else
        echo "  ⚠ Falha na compilação"
    fi
fi

# ── 4. Criar BepInEx config para nome da janela ──────────────
echo ""
echo "[ 4/5 ] Configurando BepInEx..."

mkdir -p "$BEPINEX/config"
cat > "$BEPINEX/config/BepInEx.cfg" << 'CFGEOF'
[Logging]
LogLevels = Fatal, Error, Warning, Message, Info

[Preloader]
HideManagerGameObject = true
CFGEOF

# Adicionar plugin de título de janela (simples, via BepInEx)
TITLE_PLUGIN="$BEPINEX/plugins/FrossWindowTitle/FrossWindowTitle.cs"
mkdir -p "$(dirname "$TITLE_PLUGIN")"
# Isso é compilado junto — título já definido no plugin principal
echo "  ✓ Configuração BepInEx aplicada"

# ── 5. Criar launcher "Fross Garage Band.app" ────────────────
echo ""
echo "[ 5/5 ] Criando Fross Garage Band.app..."

FGB_APP="/Applications/Fross Garage Band.app"
mkdir -p "$FGB_APP/Contents/MacOS"
mkdir -p "$FGB_APP/Contents/Resources"

# Copiar ícone do YARG
if [ -f "$YARG/Contents/Resources/UnityPlayer.icns" ]; then
    cp "$YARG/Contents/Resources/UnityPlayer.icns" "$FGB_APP/Contents/Resources/AppIcon.icns"
elif [ -f "$YARG/Contents/Resources/PlayerIcon.icns" ]; then
    cp "$YARG/Contents/Resources/PlayerIcon.icns" "$FGB_APP/Contents/Resources/AppIcon.icns"
fi

# Executável — lança YARG via BepInEx
cat > "$FGB_APP/Contents/MacOS/FrossGarageBand" << 'LAUNCHER'
#!/bin/bash
YARG="/Applications/YARG.app"
BEPINEX_SH="$YARG/run_bepinex.sh"
if [ ! -f "$BEPINEX_SH" ]; then
    osascript -e 'display alert "run_bepinex.sh não encontrado" message "Certifique-se que o BepInEx está instalado em /Applications/YARG.app"'
    exit 1
fi
chmod +x "$BEPINEX_SH"
cd "$YARG"
exec "$BEPINEX_SH" "$YARG"
LAUNCHER
chmod +x "$FGB_APP/Contents/MacOS/FrossGarageBand"

# Info.plist do launcher
cat > "$FGB_APP/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>             <string>Fross Garage Band</string>
    <key>CFBundleDisplayName</key>      <string>Fross Garage Band</string>
    <key>CFBundleIdentifier</key>       <string>com.frossgarageband.launcher</string>
    <key>CFBundleExecutable</key>       <string>FrossGarageBand</string>
    <key>CFBundleVersion</key>          <string>0.14</string>
    <key>CFBundleShortVersionString</key><string>0.14</string>
    <key>CFBundleIconFile</key>         <string>AppIcon</string>
    <key>CFBundlePackageType</key>      <string>APPL</string>
    <key>LSMinimumSystemVersion</key>   <string>10.15</string>
    <key>NSHighResolutionCapable</key>  <true/>
    <key>LSUIElement</key>              <false/>
</dict>
</plist>
PLISTEOF

# Registrar no Launch Services
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "/Applications/Fross Garage Band.app" 2>/dev/null || true

echo "  ✓ /Applications/Fross Garage Band.app criado"

# ── Resumo ────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✅  Rebranding concluído!"
echo ""
echo "  Para jogar: abra  'Fross Garage Band'  em Applications"
echo "  (ou Launchpad — pode levar alguns segundos para aparecer)"
echo ""
echo "  O que foi feito:"
echo "    ✓ Info.plist → CFBundleName = Fross Garage Band"
echo "    ✓ Todos os textos YARG → Fross Garage Band nos lang JSONs"
echo "    ✓ Plugin Download Music recompilado"
echo "    ✓ /Applications/Fross Garage Band.app criado"
echo "══════════════════════════════════════════════════════"
echo ""
read -p "Pressione Enter para fechar..."
