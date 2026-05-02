#!/bin/bash
# Fross Garage Band — Git commit & push
set -e
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

# Commit
git commit -m "feat: Fross Garage Band rebranding + native Download Music plugin

YARG → Fross Garage Band:
- rebrand_yarg.command: patches Info.plist, all 9 lang JSONs, cria
  /Applications/Fross Garage Band.app launcher
- CFBundleName = 'Fross Garage Band', version 0.14-FGB
- All lang JSONs: YARG → Fross Garage Band, Credits → Download Music

Native BepInEx Plugin (Download Music):
- compile_plugin.command: auto-compila FrossDownloadMusic.dll via dotnet
- Full Unity UI Canvas overlay (sem app externo)
- Rhythmverse API: busca, filtro por formato (chm/yarg/rb3/ps/wtde)
- Download + auto-unzip direto para pasta de músicas do YARG
- Harmony-patched no botão Credits do YARG (via reflection)

Rock Band Local pygame UI:
- ui/main_menu.py: 'Rhythmverse' → 'Download Music'
- ui/rhythmverse_screen.py: título atualizado + retry em caso de erro
- network/rhythmverse_client.py: integração real com API Rhythmverse JSON
- Launch YARG.command: launcher para YARG via BepInEx"
echo "✓ Commit criado"

# Push
echo ""
echo "▶ Fazendo push para GitHub..."
git push origin main
echo ""
echo "✅  Push concluído!"
echo "   https://github.com/rfrossard/rock-band-local"
echo ""
read -p "Pressione Enter para fechar..."
