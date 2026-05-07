#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# make_app.sh — Builds "Fross Song Manager.app" for the macOS Dock
#
# Usage:  ./make_app.sh
#
# Creates the .app bundle in the same directory as this script.
# Drag the .app to your Dock or /Applications afterward.
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Fross Song Manager"
APP_BUNDLE="$SCRIPT_DIR/$APP_NAME.app"
MACOS_DIR="$APP_BUNDLE/Contents/MacOS"
RES_DIR="$APP_BUNDLE/Contents/Resources"
LAUNCHER="$MACOS_DIR/$APP_NAME"
ICON_SRC="$SCRIPT_DIR/icon_source.png"
ICONSET="$SCRIPT_DIR/_AppIcon.iconset"
ICNS_OUT="$RES_DIR/AppIcon.icns"
PYTHON_PATH="$(command -v python3.11 || echo /Users/frossard/homebrew/bin/python3.11)"

echo "🎸  Building $APP_NAME.app..."
echo "    Project : $SCRIPT_DIR"
echo "    Python  : $PYTHON_PATH"
echo ""

# ── 0) Check Python ──────────────────────────────────────────────────────────
if [ ! -x "$PYTHON_PATH" ]; then
  echo "❌  python3.11 not found at $PYTHON_PATH"
  echo "    Brew install: brew install python@3.11"
  exit 1
fi

# ── 1) Generate icon PNG if missing ──────────────────────────────────────────
if [ ! -f "$ICON_SRC" ]; then
  echo "🖼   Generating icon..."
  "$PYTHON_PATH" "$SCRIPT_DIR/make_icon.py"
fi

# ── 2) Build .iconset ─────────────────────────────────────────────────────────
echo "🖼   Building iconset..."
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

declare -a SIZES=(16 32 64 128 256 512 1024)
for sz in "${SIZES[@]}"; do
  sips -z "$sz" "$sz" "$ICON_SRC" \
    --out "$ICONSET/icon_${sz}x${sz}.png" > /dev/null
done

# @2x variants (retina)
for sz in 16 32 64 128 256 512; do
  sz2=$((sz * 2))
  cp "$ICONSET/icon_${sz2}x${sz2}.png" \
     "$ICONSET/icon_${sz}x${sz}@2x.png"
done

# Rename to what iconutil expects
mv "$ICONSET/icon_16x16.png"      "$ICONSET/icon_16x16.png"
mv "$ICONSET/icon_32x32.png"      "$ICONSET/icon_32x32.png"
mv "$ICONSET/icon_128x128.png"    "$ICONSET/icon_128x128.png"
mv "$ICONSET/icon_256x256.png"    "$ICONSET/icon_256x256.png"
mv "$ICONSET/icon_512x512.png"    "$ICONSET/icon_512x512.png"
mv "$ICONSET/icon_1024x1024.png"  "$ICONSET/icon_512x512@2x.png"

# ── 3) Convert to .icns ───────────────────────────────────────────────────────
echo "🖼   Converting to .icns..."
mkdir -p "$RES_DIR"
iconutil -c icns "$ICONSET" --output "$ICNS_OUT"
rm -rf "$ICONSET"

# ── 4) Create directory structure ────────────────────────────────────────────
echo "📁  Creating .app structure..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RES_DIR"

# ── 5) Write launcher script ─────────────────────────────────────────────────
cat > "$LAUNCHER" << LAUNCHER_EOF
#!/usr/bin/env bash
# Fross Song Manager launcher

# ── Resolve project path ────────────────────────────────────────────────────
SELF="\$(cd "\$(dirname "\$0")" && pwd)"
BUNDLE_DIR="\$(dirname "\$(dirname "\$SELF")")"
PROJECT_DIR="\$(dirname "\$BUNDLE_DIR")"

# ── Clean Python env vars (pyenv/virtualenv inject paths that block TCC) ────
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONNOUSERSITE
unset PYENV_VERSION PYENV_ROOT PYENV_DIR PYENV_HOOK_PATH VIRTUAL_ENV

# ── Find Python.app inside Homebrew framework ──────────────────────────────
# Direct exec blocks TCC access to Documents folder; open -a grants it.
FW_PYTHON_APP=""
for candidate in \
    "/Users/frossard/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/Resources/Python.app" \
    "\$HOME/homebrew/Cellar/python@3.11"*/*/Frameworks/Python.framework/Versions/3.11/Resources/Python.app
do
  if [ -d "\$candidate" ]; then
    FW_PYTHON_APP="\$candidate"
    break
  fi
done

if [ -z "\$FW_PYTHON_APP" ]; then
  # Last resort: search
  FW_PYTHON_APP="\$(find "\$HOME/homebrew/Cellar/python@3.11" -name "Python.app" -maxdepth 8 2>/dev/null | head -1)"
fi

if [ -z "\$FW_PYTHON_APP" ]; then
  osascript -e 'display alert "Python 3.11 não encontrado" message "Instale via:\nbrew install python@3.11\nbrew install python-tk@3.11" as critical'
  exit 1
fi

# ── Verify project dir ──────────────────────────────────────────────────────
if [ ! -f "\$PROJECT_DIR/song_manager.py" ]; then
  osascript -e "display alert \"Projeto não encontrado\" message \"Esperado em:\n\$PROJECT_DIR\" as critical"
  exit 1
fi

# ── Launch via open -a (user-context, bypasses TCC for Documents folder) ────
exec /usr/bin/open -n -a "\$FW_PYTHON_APP" --args "\$PROJECT_DIR/song_manager.py"
LAUNCHER_EOF

chmod +x "$LAUNCHER"

# ── 6) Write Info.plist ───────────────────────────────────────────────────────
cat > "$APP_BUNDLE/Contents/Info.plist" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Fross Song Manager</string>
  <key>CFBundleDisplayName</key>
  <string>Fross Song Manager</string>
  <key>CFBundleIdentifier</key>
  <string>com.frossard.song-manager</string>
  <key>CFBundleVersion</key>
  <string>2.0</string>
  <key>CFBundleShortVersionString</key>
  <string>2.0</string>
  <key>CFBundleExecutable</key>
  <string>Fross Song Manager</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleSignature</key>
  <string>????</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSSupportsAutomaticGraphicsSwitching</key>
  <true/>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHumanReadableCopyright</key>
  <string>© 2026 Frossard · Matrix Edition</string>
</dict>
</plist>
PLIST_EOF

# ── 7) Clear icon cache so macOS picks up the new icon ────────────────────────
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
  -kill -r -domain local -domain system -domain user 2>/dev/null || true

# Touch so Finder refreshes icon
touch "$APP_BUNDLE"

echo ""
echo "✅  Done!  →  $APP_BUNDLE"
echo ""
echo "Next steps:"
echo "  1. Open Finder and navigate to:"
echo "     $SCRIPT_DIR"
echo "  2. Drag 'Fross Song Manager.app' to your Dock"
echo "  3. Or move it to /Applications for a permanent install:"
echo "     cp -r \"$APP_BUNDLE\" /Applications/"
echo ""
