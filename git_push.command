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
    git commit -m "fix: corrigir regressão + Download Music sem DLL patch + preview de áudio

REGRESSÃO CORRIGIDA:
- restore_yarg.command: restaura Assembly-CSharp.dll do backup, valida
  lang JSONs e corrige a chave Credits.Repos.YARG se corrompida

DOWNLOAD MUSIC (YARG) — nova abordagem, zero risco ao DLL:
- patch_download_music.command: substitui Credits.json com catálogo de
  30 coleções Rhythmverse (artistas, gêneros, busca livre)
  SpecialRole='ProjectManager' → aparece na 1ª seção da tela
  lang JSONs: header ProjectManager → '📥 Download Music' / 'Baixar Músicas'
  Cada entrada tem botão 'Website' que abre Rhythmverse pré-filtrado
  ZERO modificação em Assembly-CSharp.dll — completamente seguro

PREVIEW DE ÁUDIO (Rock Band Local Python):
- ui/song_select.py: ao navegar na lista de músicas, toca automaticamente
  preview.ogg, song.ogg, guitar.ogg etc. (em ordem de preferência)
  Duração máxima de 12 segundos, fadeout ao trocar de música
  Barra de progresso do preview na parte inferior da tela
  Para automaticamente ao iniciar o jogo ou voltar ao menu

ARQUITETURA DOWNLOAD MUSIC:
- YARG (Fross Garage Band): tela Credits → catálogo Rhythmverse (links)
- Rock Band Local (Python): '📥 Download Music' → RhythmverseScreen
  com busca completa, filtros de formato, progresso de download
  e instalação automática na pasta songs/"

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
