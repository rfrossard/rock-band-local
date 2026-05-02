#!/bin/bash
# ─────────────────────────────────────────────────────
#  Rock Band Local — GitHub setup script
#  Run once from Terminal to create repo and push.
# ─────────────────────────────────────────────────────
set -e

REPO_NAME="rock-band-local"
GITHUB_USER="rfrossard"

cd "$(dirname "$0")"

echo ""
echo "🎸 Rock Band Local — GitHub Push"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Clean up any leftover git lock ─────────────────
rm -f .git/index.lock 2>/dev/null && echo "✓ Lock removed" || true

# ── 2. Commit (if nothing committed yet) ──────────────
if git log --oneline 2>/dev/null | grep -q .; then
  echo "✓ Already committed"
else
  git add README.md LICENSE .gitignore config.json requirements.txt \
          install.sh run.sh main.py game/ ui/ network/ logos/ \
          screenshot_gameplay.png screenshot_menu.png 2>/dev/null || true
  git commit -m "Initial commit — Rock Band Local v1.0

- Full game engine: chart parser, note highway, scoring, Star Power
- Controllers: PS5 guitar (BT), PS5 drums (USB), USB mic, keyboard
- UI: main menu, song select, gameplay (3D YARG-style highway), results,
  calibration, settings, Rhythmverse browser
- Rhythmverse integration: browse and download songs in-game
- Custom YARG branding: Fross Garage Band logos + inject_logo.py"
  echo "✓ Committed"
fi

# ── 3. Create GitHub repo + push ──────────────────────
if command -v gh &>/dev/null; then
  echo ""
  echo "▶ GitHub CLI found — creating repo..."
  gh repo create "$REPO_NAME" \
    --public \
    --description "Local Rock Band game for macOS — YARG + Clone Hero + Frets on Fire" \
    --source=. \
    --remote=origin \
    --push
  echo ""
  echo "✅ Done! Repo live at: https://github.com/$GITHUB_USER/$REPO_NAME"

else
  echo ""
  echo "⚠️  GitHub CLI (gh) not found."
  echo ""
  echo "Option A — Install gh and re-run this script:"
  echo "  brew install gh && gh auth login && bash push_to_github.sh"
  echo ""
  echo "Option B — Manual push:"
  echo "  1. Go to https://github.com/new"
  echo "  2. Name: $REPO_NAME | Public | NO README/gitignore"
  echo "  3. Run:"
  echo "     git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
  echo "     git push -u origin main"
fi
