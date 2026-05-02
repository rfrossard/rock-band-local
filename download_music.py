#!/usr/bin/env python3
"""
Fross Garage Band — Download Music
===================================
Abre direto na tela de download do Rhythmverse.
Pode ser lançado standalone (via .command, .app ou Terminal)
ou pelo menu principal do Rock Band Local.

Uso:
    python3 download_music.py              # tela Rhythmverse
    python3 download_music.py --query "metallica"   # busca direta
    python3 download_music.py --format chm          # filtro por formato
"""
from __future__ import annotations
import argparse
import json
import os
import sys

# ── Caminho raiz do projeto ──────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

SONGS_DIR   = os.path.join(PROJECT_DIR, "songs")
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")

os.makedirs(SONGS_DIR, exist_ok=True)

# ── Argumentos ───────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Fross Garage Band — Download Music")
parser.add_argument("--query",  "-q", default="",    help="Busca inicial")
parser.add_argument("--format", "-f", default="all", help="Filtro de gameformat (chm, yarg, rb3, all...)")
parser.add_argument("--headless", action="store_true", help="Modo sem UI: busca e baixa via terminal")
parser.add_argument("--limit",  "-l", type=int, default=20, help="Limite de resultados (modo headless)")
args = parser.parse_args()

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    cfg = {
        "rhythmverse": {
            "base_url": "https://rhythmverse.co",
            "download_path": SONGS_DIR,
            "cache_ttl_seconds": 120,
            "records_per_page": 25,
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                stored = json.load(f)
            if "rhythmverse" in stored:
                cfg["rhythmverse"].update(stored["rhythmverse"])
            # Sempre usar SONGS_DIR como destino
            cfg["rhythmverse"]["download_path"] = SONGS_DIR
        except Exception:
            pass
    return cfg

config = load_config()

# ─────────────────────────────────────────────────────────────────────────────
# MODO HEADLESS — busca + download via terminal (sem pygame)
# ─────────────────────────────────────────────────────────────────────────────
if args.headless:
    from network.rhythmverse_client import RhythmverseClient

    client = RhythmverseClient(config, download_dir=SONGS_DIR)
    print(f"\n🎸 Fross Garage Band — Download Music (headless)")
    print(f"   Destino: {SONGS_DIR}\n")

    result = client.search(args.query, gameformat=args.format, records=args.limit)
    print(f"Encontradas: {result.total_songs:,} músicas\n")

    for i, song in enumerate(result.songs):
        dl = "✅" if song.has_direct_download else "🔗"
        print(f"  {i+1:2d}. {dl} [{song.gameformat}] {song.display_name}")
        if song.duration_sec:
            m, s = divmod(song.duration_sec, 60)
            print(f"       Duração: {m}:{s:02d} | Downloads: {song.downloads:,}")

    print()
    choice = input("Número da música para baixar (Enter para sair): ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(result.songs):
            song = result.songs[idx]
            if not song.has_direct_download:
                print(f"⚠ Sem download direto. Acesse: {song.download_page_url}")
            else:
                print(f"⬇ Baixando: {song.display_name}...")
                def cb(p):
                    bar = "█" * int(p * 30) + "░" * (30 - int(p * 30))
                    print(f"\r  [{bar}] {p*100:.0f}%", end="", flush=True)
                dest = client.download_song(song, progress_cb=cb)
                print()
                if dest:
                    print(f"✅ Salvo em: {dest}")
                    print("   A música aparecerá automaticamente no YARG na próxima varredura.")
                else:
                    print("❌ Falha no download.")
    sys.exit(0)

# ─────────────────────────────────────────────────────────────────────────────
# MODO GUI — abre janela pygame com tela Rhythmverse
# ─────────────────────────────────────────────────────────────────────────────
import pygame

from game.constants import (
    SCREEN_W, SCREEN_H, COLOR_BG, WHITE, STATE_QUIT,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE,
)
from ui.base_screen import draw_text
from ui.rhythmverse_screen import RhythmverseScreen


class DownloadMusicApp:
    """Janela standalone só com a tela de download Rhythmverse."""

    def __init__(self):
        pygame.init()
        pygame.mixer.quit()  # sem áudio necessário aqui
        pygame.display.set_caption("Fross Garage Band — Download Music")

        # Ícone
        icon_path = os.path.join(PROJECT_DIR, "logos", "YARG_Colorless.png")
        if os.path.exists(icon_path):
            try:
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)
            except Exception:
                pass

        flags = pygame.RESIZABLE
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        self.clock  = pygame.time.Clock()

        self.rv_screen = RhythmverseScreen(self.screen, config)
        # Pre-fill query/format from args
        self.rv_screen._input_text  = args.query
        self.rv_screen._gameformat  = args.format
        self.rv_screen.on_enter()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE)
                    self.rv_screen.screen = self.screen
                    self.rv_screen.w = event.w
                    self.rv_screen.h = event.h
                else:
                    # Block transition_to(STATE_QUIT/MAIN_MENU) → just close
                    try:
                        self.rv_screen.handle_event(event)
                    except SystemExit:
                        running = False

            # Redirect "go to main menu" → close window
            if getattr(self.rv_screen, '_next_state', None) in (
                    'main_menu', 'quit', STATE_QUIT):
                running = False

            self.rv_screen.update(dt)
            self.rv_screen.draw()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    app = DownloadMusicApp()
    app.run()
