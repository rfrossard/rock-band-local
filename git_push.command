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
    git commit -m "feat: v2.2.0 — YARG Music Library visual redesign + download fix

FIX: Download travado (Application.OpenURL)
- Download coroutine substituído por Application.OpenURL
- Rhythmverse exige cookies de browser para download direto
- Agora abre o link no navegador do sistema automaticamente

FIX: Cards invisíveis no scroll (RectMask2D)
- Causa raiz: Image+Mask com alpha=0 não escreve no stencil buffer
- Fix: Viewport usa RectMask2D (clip por RectTransform, sem stencil)
- anchoredPosition resetado diretamente em RebuildCards

REDESIGN: FrossDownloadMenu.cs — visual YARG Music Library
- Paleta: bg=#07101C, panel=#0D1B2B, seleção=#1478FF, texto branco
- TopBar: 64px, título MUSIC LIBRARY + caption DOWNLOAD (estilo YARG)
- Layout: 65% lista / 35% detalhe com separador vertical
- Linhas de 54px (era 70px): título branco esq + artista cinza itálico dir
- Badge de formato no canto superior direito de cada linha
- Separador fino C_SEP entre linhas (6% branco)
- Seleção: fundo azul full-width (sem border strip lateral)
- Botão BAIXAR no topo do painel de detalhe (estilo PLAY SONG do YARG)
- Botões de formato: pills transparentes com highlight no selecionado"

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
