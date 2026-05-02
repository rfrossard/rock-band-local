#!/bin/bash
# Fix: remove token from history and push clean
set -e
cd "$(dirname "$0")"

echo ""
echo "🔒  Fross Garage Band — Fix & Push"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Desfazer o último commit (mantém as mudanças staged)
echo "[1/4] Desfazendo último commit..."
git reset --soft HEAD~1
echo "✓ Commit desfeito"

# 2. Limpar final_push.command (remover token)
echo "[2/4] Limpando final_push.command..."
cat > final_push.command << 'SCRIPT'
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
SCRIPT
echo "✓ Token removido"

# 3. Re-adicionar e re-commitar
echo "[3/4] Recriando commit limpo..."
git add -A
git commit -m "feat: Fross Garage Band rebranding + native Download Music plugin

YARG → Fross Garage Band:
- rebrand_yarg.command: patches Info.plist, all 9 lang JSONs, cria
  /Applications/Fross Garage Band.app launcher
- CFBundleName = Fross Garage Band, version 0.14-FGB
- All lang JSONs: YARG → Fross Garage Band, Credits → Download Music

Native BepInEx Plugin (Download Music):
- compile_plugin.command: auto-compila FrossDownloadMusic.dll via dotnet
- Full Unity UI Canvas overlay (sem app externo)
- Rhythmverse API: busca + filtro por formato (chm/yarg/rb3/ps/wtde)
- Download + auto-unzip direto para pasta de musicas do YARG
- Harmony-patched no botao Credits do YARG (via reflection)

Rock Band Local pygame UI:
- ui/main_menu.py: Rhythmverse -> Download Music
- ui/rhythmverse_screen.py: titulo atualizado + retry em caso de erro
- network/rhythmverse_client.py: integracao real com API Rhythmverse JSON
- Launch YARG.command: launcher para YARG via BepInEx"
echo "✓ Commit limpo criado"

# 4. Push
echo "[4/4] Fazendo push..."
git push origin main
echo ""
echo "✅  Push concluído!"
echo "   https://github.com/rfrossard/rock-band-local"
echo ""
read -p "Pressione Enter para fechar..."
