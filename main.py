"""
Rock Band Local
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Combinando o melhor de YARG, Clone Hero, Frets on Fire
e Guitar Hero World Tour Definitive Edition.

Suporte a:
  • Guitarra Rock Band PS5 (Bluetooth)
  • Bateria Rock Band PS5 (USB HID)
  • Microfone USB (detecção de pitch vocal)
  • Teclado (fallback para todos os instrumentos)
  • Charts .chart (Clone Hero) e .mid básico
  • Busca e download de músicas via Rhythmverse.co
  • Star Power / Overdrive
  • Multiplayer local até 4 jogadores
  • Calibração de latência de áudio
"""
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import pygame

# ── Constants ─────────────────────────────────────────────────────────────────
from game.constants import (
    SCREEN_W, SCREEN_H,
    STATE_MAIN_MENU, STATE_SONG_SELECT, STATE_GAMEPLAY,
    STATE_RESULTS, STATE_CALIBRATION, STATE_RHYTHMVERSE,
    STATE_SETTINGS, STATE_QUIT,
    COLOR_BG, WHITE,
)

# ── Engines ───────────────────────────────────────────────────────────────────
from game.audio_engine import AudioEngine
from game.input_handler import InputManager

# ── Screens ───────────────────────────────────────────────────────────────────
from ui.main_menu        import MainMenu
from ui.song_select      import SongSelectScreen
from ui.gameplay_screen  import GameplayScreen
from ui.results_screen   import ResultsScreen
from ui.calibration_screen import CalibrationScreen
from ui.rhythmverse_screen import RhythmverseScreen
from ui.settings_screen  import SettingsScreen
from ui.base_screen      import draw_text


CONFIG_PATH = "config.json"


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> Dict:
    """Carrega config.json ou retorna defaults se não existir."""
    defaults = {
        "audio": {
            "latency_offset_ms": 0,
            "master_volume": 0.8,
            "song_volume": 1.0,
            "guitar_volume": 1.0,
            "bass_volume": 1.0,
            "drums_volume": 1.0,
            "vocals_volume": 1.0,
            "mic_device_index": None,
        },
        "video": {
            "width": SCREEN_W,
            "height": SCREEN_H,
            "fullscreen": False,
            "fps_cap": 60,
            "note_speed": 5,
        },
        "gameplay": {
            "difficulty": "medium",
            "note_highway_length_ms": 2000,
            "hit_window_perfect_ms": 20,
            "hit_window_good_ms": 45,
            "hit_window_ok_ms": 70,
        },
        "songs_path": "songs",
        "rhythmverse": {
            "base_url": "https://rhythmverse.co",
            "download_path": "songs",
            "cache_ttl_seconds": 300,
        },
        "players": [
            {"instrument": "guitar", "difficulty": "medium"},
        ],
    }

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                stored = json.load(f)
            # Merge profundo
            _deep_merge(defaults, stored)
        except Exception as e:
            print(f"[Config] Erro ao ler config.json: {e}. Usando defaults.")

    # Garantir pasta de músicas
    songs_dir = defaults.get("songs_path", "songs")
    os.makedirs(songs_dir, exist_ok=True)

    return defaults


def _deep_merge(base: Dict, override: Dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


# ── Game class ────────────────────────────────────────────────────────────────

class RockBandLocal:

    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
        except Exception as e:
            print(f"⚠️   Mixer indisponível ({e}) — jogo sem áudio.")
        pygame.font.init()

        self._config = load_config()
        video = self._config.get("video", {})

        # Janela
        flags = pygame.FULLSCREEN if video.get("fullscreen") else 0
        self._screen = pygame.display.set_mode(
            (video.get("width", SCREEN_W), video.get("height", SCREEN_H)),
            flags | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption("Rock Band Local 🎸")
        try:
            icon = pygame.Surface((32, 32))
            icon.fill((20, 20, 40))
            pygame.draw.circle(icon, (220, 200, 30), (16, 16), 14)
            pygame.draw.circle(icon, (20, 20, 40), (16, 16), 10)
            pygame.display.set_icon(icon)
        except Exception:
            pass

        self._clock = pygame.time.Clock()
        self._fps   = video.get("fps_cap", 60)
        self._running = True

        # Shared engines
        self._audio     = AudioEngine(self._config)
        self._input_mgr = InputManager(self._config)
        self._input_mgr.setup_players(self._config.get("players", [
            {"instrument": "guitar", "difficulty": "medium"}
        ]))

        # Tela atual
        self._state: str = STATE_MAIN_MENU
        self._screen_obj: Any = None
        self._transition_to(STATE_MAIN_MENU)

    # ── State machine ─────────────────────────────────────────────────────────

    def _transition_to(self, state: str, data: Optional[Dict] = None) -> None:
        """Cria e ativa a tela correspondente ao estado."""
        self._state = state

        # Ao sair do gameplay, para o áudio
        if hasattr(self._screen_obj, '_audio'):
            pass  # AudioEngine é compartilhado — não stop aqui

        if state == STATE_MAIN_MENU:
            self._screen_obj = MainMenu(self._screen, self._config)

        elif state == STATE_SONG_SELECT:
            obj = SongSelectScreen(self._screen, self._config)
            obj.on_enter()
            self._screen_obj = obj

        elif state == STATE_GAMEPLAY:
            if not data:
                self._transition_to(STATE_SONG_SELECT)
                return
            # Re-setup de jogadores conforme config atual
            self._input_mgr.setup_players(self._config.get("players", [
                {"instrument": "guitar", "difficulty": "medium"}
            ]))
            # Sync player_cfgs com data
            data['players'] = self._config.get("players", data.get("players", []))
            self._audio.unload()
            obj = GameplayScreen(
                self._screen, self._config, data,
                self._input_mgr, self._audio,
            )
            self._screen_obj = obj

        elif state == STATE_RESULTS:
            self._screen_obj = ResultsScreen(self._screen, self._config, data or {})

        elif state == STATE_CALIBRATION:
            self._screen_obj = CalibrationScreen(self._screen, self._config, self._audio)

        elif state == STATE_RHYTHMVERSE:
            obj = RhythmverseScreen(self._screen, self._config)
            obj.on_enter()
            self._screen_obj = obj

        elif state == STATE_SETTINGS:
            self._screen_obj = SettingsScreen(self._screen, self._config)

        elif state == STATE_QUIT:
            self._running = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Loop principal do jogo."""
        while self._running:
            dt = self._clock.tick(self._fps) / 1000.0
            dt = min(dt, 0.05)  # cap em 50ms para evitar saltos em lag

            # Eventos globais
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()

            # Delegar eventos à tela atual
            if self._screen_obj:
                for event in events:
                    self._screen_obj.handle_event(event)

                self._screen_obj.update(dt)
                self._screen_obj.draw()

                # Verificar transição de estado
                if self._screen_obj.next_state:
                    next_s = self._screen_obj.next_state
                    next_d = self._screen_obj.next_data
                    self._screen_obj.next_state = None
                    self._screen_obj.next_data  = None
                    self._transition_to(next_s, next_d)

            # FPS counter (debug)
            fps_actual = self._clock.get_fps()
            draw_text(self._screen, f"{fps_actual:.0f} fps",
                      self._screen.get_width() - 8, 4,
                      size=12, color=(40, 40, 60),
                      center_x=False)

            pygame.display.flip()

        self._shutdown()

    def _toggle_fullscreen(self) -> None:
        video = self._config.get("video", {})
        full  = not video.get("fullscreen", False)
        video["fullscreen"] = full
        self._config["video"] = video
        flags = pygame.FULLSCREEN if full else 0
        self._screen = pygame.display.set_mode(
            (video.get("width", SCREEN_W), video.get("height", SCREEN_H)),
            flags | pygame.DOUBLEBUF,
        )
        # Re-injetar tela com nova surface
        if self._screen_obj:
            self._screen_obj.screen = self._screen
            self._screen_obj.w = self._screen.get_width()
            self._screen_obj.h = self._screen.get_height()

    def _shutdown(self) -> None:
        self._input_mgr.shutdown()
        self._audio.unload()
        pygame.quit()


# ── Entry point ───────────────────────────────────────────────────────────────

def check_dependencies() -> bool:
    """Verifica dependências críticas antes de iniciar."""
    missing = []
    try:
        import pygame   # noqa: F401
    except ImportError:
        missing.append("pygame")
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import bs4  # noqa: F401
    except ImportError:
        missing.append("beautifulsoup4")

    if missing:
        print("❌  Dependências faltando. Execute:")
        print(f"    pip install {' '.join(missing)}")
        return False

    # Opcionais
    optionals = []
    try:
        import sounddevice  # noqa: F401
        import aubio        # noqa: F401
    except ImportError:
        optionals.append("sounddevice aubio  # detecção de pitch vocal")
    try:
        import numpy  # noqa: F401
    except ImportError:
        optionals.append("numpy  # necessário para vocal e beep de calibração")

    if optionals:
        print("⚠️   Dependências opcionais não instaladas:")
        for o in optionals:
            print(f"    pip install {o}")
        print("    (o jogo funcionará sem vocal e alguns efeitos)")

    return True


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    print("🎸  Rock Band Local — iniciando...")
    print("    F11 = Fullscreen   P = Pause   ESC = Voltar\n")

    try:
        game = RockBandLocal()
        game.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        print(f"\n💥  Erro fatal: {e}")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
