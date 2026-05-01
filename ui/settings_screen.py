"""
Rock Band Local — Settings Screen
Configura volume, nota speed, número de jogadores, joysticks e mapeamentos.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import pygame

from game.input_handler import InputManager
from game.constants import (
    STATE_MAIN_MENU,
    INSTRUMENTS, DIFFICULTIES,
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
    DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT,
    COLOR_BG, WHITE, GRAY, DGRAY, COLOR_STAR, FRET_COLORS,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect
from ui.song_select import INSTRUMENT_ICONS, DIFF_COLORS


CONFIG_PATH = "config.json"

INSTRUMENT_LABELS = {
    INSTRUMENT_GUITAR: "🎸 Guitarra",
    INSTRUMENT_BASS:   "🎵 Baixo",
    INSTRUMENT_DRUMS:  "🥁 Bateria",
    INSTRUMENT_VOCALS: "🎤 Vocal",
}

DIFF_LABELS = {
    DIFF_EASY:   "Fácil",
    DIFF_MEDIUM: "Médio",
    DIFF_HARD:   "Difícil",
    DIFF_EXPERT: "Expert",
}


class Slider:
    """Controle deslizante horizontal."""

    def __init__(self, rect: pygame.Rect, value: float,
                 min_val: float = 0.0, max_val: float = 1.0,
                 label: str = "", fmt: str = ".0%"):
        self.rect = rect
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.label = label
        self.fmt = fmt
        self._dragging = False

    @property
    def fill_x(self) -> int:
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(0, 20).collidepoint(event.pos):
                self._dragging = True
                self._set_from_mouse(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._set_from_mouse(event.pos[0])
            return True
        return False

    def _set_from_mouse(self, mx: int) -> None:
        ratio = max(0.0, min(1.0, (mx - self.rect.x) / self.rect.width))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def draw(self, surface: pygame.Surface) -> None:
        # Track
        pygame.draw.rect(surface, DGRAY, self.rect, border_radius=4)
        # Fill
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, self.fill_x - self.rect.x, self.rect.height)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, COLOR_STAR, fill_rect, border_radius=4)
        # Knob
        pygame.draw.circle(surface, WHITE, (self.fill_x, self.rect.centery), 9)
        # Label
        draw_text(surface, self.label, self.rect.x, self.rect.y - 18,
                  size=FONT_TINY_SIZE, color=GRAY)
        # Value
        val_str = format(self.value, self.fmt) if self.fmt else str(self.value)
        draw_text(surface, val_str, self.rect.right, self.rect.y - 18,
                  size=FONT_TINY_SIZE, color=WHITE)


class SettingsScreen(BaseScreen):
    """
    Tela de configurações dividida em abas:
      Audio | Vídeo | Jogadores | Controles
    """

    TABS = ["🔊 Áudio", "🎮 Jogadores", "🕹️  Controles", "🎬 Vídeo"]

    def __init__(self, screen: pygame.Surface, config: Dict):
        super().__init__(screen, config)
        self._tab = 0
        self._sliders: List[Slider] = []
        self._dirty = False

        # Joysticks detectados
        self._joysticks = InputManager.list_joysticks()

        self._btn_back = Button(
            pygame.Rect(20, self.h - 70, 130, 46),
            "← Voltar",
            color=(60, 60, 80),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_save = Button(
            pygame.Rect(self.w - 170, self.h - 70, 150, 46),
            "💾  Salvar",
            color=(30, 80, 150),
            font_size=FONT_TINY_SIZE,
        )
        self._buttons = [self._btn_back, self._btn_save]

        # Tabs buttons
        tab_w = 160
        tab_y = 58
        self._tab_buttons: List[Button] = []
        for i, label in enumerate(self.TABS):
            btn = Button(
                pygame.Rect(20 + i * (tab_w + 8), tab_y, tab_w, 36),
                label,
                color=(35, 35, 55),
                hover_color=(50, 50, 80),
                font_size=FONT_TINY_SIZE,
            )
            self._tab_buttons.append(btn)

        self._rebuild_sliders()

    # ── Sliders ───────────────────────────────────────────────────────────────

    def _rebuild_sliders(self) -> None:
        self._sliders.clear()
        audio = self.config.get('audio', {})
        video = self.config.get('video', {})

        if self._tab == 0:  # Audio
            items = [
                ('master_volume',  "Volume Mestre",     audio.get('master_volume', 0.8)),
                ('song_volume',    "Música de Fundo",   audio.get('song_volume', 1.0)),
                ('guitar_volume',  "Guitarra",          audio.get('guitar_volume', 1.0)),
                ('bass_volume',    "Baixo",             audio.get('bass_volume', 1.0)),
                ('drums_volume',   "Bateria",           audio.get('drums_volume', 1.0)),
                ('vocals_volume',  "Vocais",            audio.get('vocals_volume', 1.0)),
            ]
            sx, sw, sy = 80, 500, 140
            for i, (key, label, val) in enumerate(items):
                s = Slider(
                    pygame.Rect(sx, sy + i * 60, sw, 12),
                    val, 0.0, 1.0, label,
                )
                s._key = ('audio', key)
                self._sliders.append(s)

        elif self._tab == 3:  # Video
            note_speed = video.get('note_speed', 5)
            s_speed = Slider(
                pygame.Rect(80, 140, 400, 12),
                note_speed, 1, 10, "Velocidade das Notas", ".0f",
            )
            s_speed._key = ('video', 'note_speed')
            self._sliders.append(s_speed)

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._dirty:
                self._save_config()
            self.transition_to(STATE_MAIN_MENU)

        # Tab clicks
        for i, btn in enumerate(self._tab_buttons):
            if btn.is_clicked(event):
                self._tab = i
                self._rebuild_sliders()

        # Sliders
        for s in self._sliders:
            if s.handle_event(event):
                key_path = getattr(s, '_key', None)
                if key_path:
                    section, key = key_path
                    self.config.setdefault(section, {})[key] = s.value
                    self._dirty = True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._btn_back.is_clicked(event):
                if self._dirty:
                    self._save_config()
                self.transition_to(STATE_MAIN_MENU)
            elif self._btn_save.is_clicked(event):
                self._save_config()
                self.transition_to(STATE_MAIN_MENU)
            self._handle_player_clicks(event)
            self._handle_js_clicks(event)

    def _handle_player_clicks(self, event: pygame.event.Event) -> None:
        if self._tab != 1:
            return
        players = self.config.setdefault('players', [{'instrument': INSTRUMENT_GUITAR, 'difficulty': DIFF_MEDIUM}])

        # Botão adicionar jogador
        add_rect = pygame.Rect(20, 135 + len(players) * 70, 120, 32)
        if event.type == pygame.MOUSEBUTTONDOWN and add_rect.collidepoint(event.pos) and len(players) < 4:
            players.append({'instrument': INSTRUMENT_GUITAR, 'difficulty': DIFF_MEDIUM})
            self._dirty = True
            return

        for i, p in enumerate(players):
            y = 140 + i * 70

            # Remover
            rem_rect = pygame.Rect(self.w - 60, y + 10, 40, 28)
            if event.type == pygame.MOUSEBUTTONDOWN and rem_rect.collidepoint(event.pos) and len(players) > 1:
                players.pop(i)
                self._dirty = True
                return

            # Instrumento cycle
            inst_rect = pygame.Rect(200, y + 8, 160, 30)
            if event.type == pygame.MOUSEBUTTONDOWN and inst_rect.collidepoint(event.pos):
                idx = INSTRUMENTS.index(p.get('instrument', INSTRUMENT_GUITAR))
                p['instrument'] = INSTRUMENTS[(idx + 1) % len(INSTRUMENTS)]
                self._dirty = True

            # Dificuldade cycle
            diff_rect = pygame.Rect(380, y + 8, 120, 30)
            if event.type == pygame.MOUSEBUTTONDOWN and diff_rect.collidepoint(event.pos):
                idx = DIFFICULTIES.index(p.get('difficulty', DIFF_MEDIUM))
                p['difficulty'] = DIFFICULTIES[(idx + 1) % len(DIFFICULTIES)]
                self._dirty = True

    def _handle_js_clicks(self, event: pygame.event.Event) -> None:
        if self._tab != 2:
            return
        # Botão "Redetectar joysticks"
        btn_rect = pygame.Rect(20, self.h - 120, 200, 36)
        if event.type == pygame.MOUSEBUTTONDOWN and btn_rect.collidepoint(event.pos):
            pygame.joystick.init()
            self._joysticks = InputManager.list_joysticks()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        super().update(dt)
        for btn in self._tab_buttons:
            btn.update(pygame.mouse.get_pos())

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self.draw_title("Configurações", y=20)

        # Tabs
        for i, btn in enumerate(self._tab_buttons):
            color = (50, 50, 90) if i == self._tab else (35, 35, 55)
            border = FRET_COLORS[i % 5] if i == self._tab else None
            draw_rounded_rect(self.screen, btn.rect, color, radius=8,
                              border_color=border, border_width=2)
            draw_text(self.screen, btn.label, btn.rect.centerx, btn.rect.centery,
                      size=FONT_TINY_SIZE, color=WHITE, center_x=True, center_y=True)

        # Conteúdo da aba
        if self._tab == 0:
            self._draw_audio_tab()
        elif self._tab == 1:
            self._draw_players_tab()
        elif self._tab == 2:
            self._draw_controls_tab()
        elif self._tab == 3:
            self._draw_video_tab()

        self._btn_back.draw(self.screen)
        self._btn_save.draw(self.screen)

        if self._dirty:
            draw_text(self.screen, "● Alterações não salvas",
                      self.w // 2, self.h - 55,
                      size=FONT_TINY_SIZE, color=(255, 180, 50), center_x=True)

    def _draw_audio_tab(self) -> None:
        for s in self._sliders:
            s.draw(self.screen)
        audio = self.config.get('audio', {})
        offset = audio.get('latency_offset_ms', 0.0)
        draw_text(self.screen, f"Offset de latência: {offset:+.1f} ms",
                  80, self.h - 150,
                  size=FONT_TINY_SIZE, color=GRAY)
        draw_text(self.screen, "(Ajuste na tela Calibração de Latência)",
                  80, self.h - 130,
                  size=FONT_TINY_SIZE, color=(60, 60, 80))

    def _draw_players_tab(self) -> None:
        players = self.config.get('players', [])
        draw_text(self.screen, "Jogadores (até 4):", 20, 110,
                  size=FONT_SMALL_SIZE, color=GRAY)

        for i, p in enumerate(players):
            y = 140 + i * 70
            inst = p.get('instrument', INSTRUMENT_GUITAR)
            diff = p.get('difficulty', DIFF_MEDIUM)

            draw_rounded_rect(self.screen, pygame.Rect(20, y, self.w - 80, 50),
                              (30, 30, 50), radius=8,
                              border_color=FRET_COLORS[i % 5], border_width=1)

            draw_text(self.screen, f"P{i + 1}", 50, y + 15,
                      size=FONT_SMALL_SIZE, bold=True, color=WHITE)

            # Instrumento
            draw_rounded_rect(self.screen, pygame.Rect(200, y + 8, 160, 30),
                              (45, 45, 70), radius=6)
            draw_text(self.screen, INSTRUMENT_LABELS.get(inst, inst),
                      280, y + 23, size=FONT_TINY_SIZE, color=WHITE,
                      center_x=True, center_y=True)

            # Dificuldade
            diff_color = DIFF_COLORS.get(diff, GRAY)
            draw_rounded_rect(self.screen, pygame.Rect(380, y + 8, 120, 30),
                              diff_color, radius=6)
            draw_text(self.screen, DIFF_LABELS.get(diff, diff),
                      440, y + 23, size=FONT_TINY_SIZE, color=WHITE,
                      center_x=True, center_y=True)

            # Remover
            if len(players) > 1:
                rem_rect = pygame.Rect(self.w - 60, y + 10, 40, 28)
                draw_rounded_rect(self.screen, rem_rect, (100, 30, 30), radius=6)
                draw_text(self.screen, "✕", rem_rect.centerx, rem_rect.centery,
                          size=FONT_TINY_SIZE, color=WHITE,
                          center_x=True, center_y=True)

        # Botão adicionar
        if len(players) < 4:
            ay = 135 + len(players) * 70
            add_rect = pygame.Rect(20, ay, 120, 32)
            draw_rounded_rect(self.screen, add_rect, (30, 80, 30), radius=6)
            draw_text(self.screen, "+ Jogador", add_rect.centerx, add_rect.centery,
                      size=FONT_TINY_SIZE, color=WHITE, center_x=True, center_y=True)

        draw_text(self.screen, "(Clique no instrumento ou dificuldade para alternar)",
                  20, self.h - 140, size=FONT_TINY_SIZE, color=(60, 60, 80))

    def _draw_controls_tab(self) -> None:
        draw_text(self.screen, "Joysticks detectados:", 20, 105,
                  size=FONT_SMALL_SIZE, color=GRAY)

        if not self._joysticks:
            draw_text(self.screen, "Nenhum joystick detectado.",
                      20, 135, size=FONT_TINY_SIZE, color=(180, 60, 60))
        else:
            for i, js in enumerate(self._joysticks):
                y = 135 + i * 50
                draw_rounded_rect(self.screen, pygame.Rect(20, y, self.w - 40, 42),
                                  (28, 28, 45), radius=8)
                draw_text(self.screen, f"#{js['id']}  {js['name']}",
                          30, y + 6, size=FONT_TINY_SIZE, color=WHITE)
                draw_text(self.screen,
                          f"Axes: {js['axes']}   Botões: {js['buttons']}   Hats: {js['hats']}",
                          30, y + 24, size=FONT_TINY_SIZE, color=GRAY)

        # Reload button
        btn_y = self.h - 120
        reload_rect = pygame.Rect(20, btn_y, 220, 36)
        draw_rounded_rect(self.screen, reload_rect, (40, 60, 100), radius=8)
        draw_text(self.screen, "🔄  Redetectar Joysticks",
                  reload_rect.centerx, reload_rect.centery,
                  size=FONT_TINY_SIZE, color=WHITE, center_x=True, center_y=True)

        # Keyboard map
        draw_text(self.screen, "Teclado — Guitarra P1:", 20, btn_y - 100,
                  size=FONT_TINY_SIZE, color=GRAY)
        draw_text(self.screen, "Frets: S D F J K   |   Strum: ↑↓   |   Star Power: ESPAÇO",
                  20, btn_y - 78, size=FONT_TINY_SIZE, color=WHITE)
        draw_text(self.screen, "Teclado — Bateria P1:",
                  20, btn_y - 55, size=FONT_TINY_SIZE, color=GRAY)
        draw_text(self.screen, "Pads: V F G H J  (kick, red, yellow, blue, green)",
                  20, btn_y - 33, size=FONT_TINY_SIZE, color=WHITE)

    def _draw_video_tab(self) -> None:
        for s in self._sliders:
            s.draw(self.screen)

        video = self.config.get('video', {})
        fullscreen = video.get('fullscreen', False)
        fps = video.get('fps_cap', 60)

        y = 220
        draw_rounded_rect(self.screen, pygame.Rect(80, y, 200, 36),
                          (50, 50, 80) if fullscreen else (30, 30, 50), radius=8,
                          border_color=(80, 120, 200) if fullscreen else None, border_width=2)
        draw_text(self.screen, f"Tela Cheia: {'✓ Ligado' if fullscreen else '✗ Desligado'}",
                  180, y + 18, size=FONT_TINY_SIZE, color=WHITE,
                  center_x=True, center_y=True)

        draw_text(self.screen, f"FPS máx: {fps}", 80, y + 55,
                  size=FONT_TINY_SIZE, color=GRAY)
        draw_text(self.screen, "Nota: resolução e fullscreen requerem reiniciar.",
                  80, y + 78, size=FONT_TINY_SIZE, color=(60, 60, 80))

    # ── Persistência ──────────────────────────────────────────────────────────

    def _save_config(self) -> None:
        try:
            # Sincroniza players do config
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    stored = json.load(f)
            else:
                stored = {}

            # Merge profundo
            for section, values in self.config.items():
                if isinstance(values, dict):
                    stored.setdefault(section, {}).update(values)
                else:
                    stored[section] = values

            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(stored, f, indent=2, ensure_ascii=False)

            self._dirty = False
        except Exception as e:
            print(f"[Settings] Erro ao salvar config: {e}")
