#!/bin/bash
# Rock Band Local — Push to GitHub
# Token removed for security. Use: gh auth login
set -e
cd "$(dirname "$0")"
echo ""
echo "🎸 Rock Band Local — Pushing to GitHub"
echo "Please authenticate first: gh auth login"
git push -u origin main
echo "✅ Done!"
read -p "Press Enter to close..."
