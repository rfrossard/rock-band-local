#!/bin/bash
# Fross Garage Band — Git commit & push
cd "$(dirname "$0")"

echo ""
echo "🎸  Fross Garage Band — GitHub Push"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Limpar lock se existir
rm -f .git/index.lock 2>/dev/null && echo "✓ Lock removido" || true

# Stage de tudo
git add -A
echo "✓ Arquivos adicionados"

# Verifica se há algo para commitar
if git diff --cached --quiet; then
    echo "  (nada novo para commitar — tudo já está no histórico)"
else
    git commit -m "feat: v2.0.0 — FrossDownloadMenu Unity C# in-game Rhythmverse search

YARG IS NOW THE PRIMARY GAME:
- Python Rock Band Local archived to backup/python_rb_local/
- YARG (Fross Garage Band) is the sole game
- All new features built in Unity C#

NEW: FrossDownloadMenu.cs (~550 lines)
- Full Unity C# MonoBehaviour — no Unity Editor required
- Programmatic Canvas overlay (sortingOrder=200) on top of YARG UI
- Search bar + format filter buttons (All/CH/YARG/RB3/PS/WTDE)
- Scrollable song list with difficulty chips per instrument
- Detail panel: title, artist, album, diffs, download count
- Download button with real-time progress bar
- UnityWebRequest coroutines → Rhythmverse POST API
- ZIP extraction → ~/Library/Application Support/YARG/songs/
- Back button — overlay destroyed, YARG resumes normally

NEW: patch_fgb.command
- Compiles FrossDownloadMenu.cs → FrossDownloadMenu.dll (net472)
- References YARG's own UnityEngine / UI DLLs at compile time
- Copies DLL to YARG Managed/ folder
- Mono.Cecil inline patcher: MainMenu.Credits() → FrossDownloadMenu.Show()
- Re-signs Assembly-CSharp.dll with codesign
- Backup before patch → restore_yarg.command still works

NEW: IMPLEMENTATION_PLAN.md
- Session continuity document: what's done, what's next
- Phase-by-phase status (Phases 1-5)
- API reference, architecture diagram, session notes
- Token budget strategy for future Claude sessions

UPDATED: README.md → v2.0.0
- Unity-first architecture description
- Quick start with patch_fgb.command
- Scripts reference table
- Changelog"

    echo "✓ Commit criado"
fi

# Push
echo ""
echo "▶ Fazendo push para GitHub..."
git push origin main
echo ""
echo "✅  Push concluído!"
echo "   https://github.com/rfrossard/rock-band-local"
echo ""
read -p "Pressione Enter para fechar..."
