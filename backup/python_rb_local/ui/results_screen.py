"""
Rock Band Local — Results Screen
"""
from __future__ import annotations
import math
import time
from typing import Dict, List

import pygame

from game.constants import (
    STATE_SONG_SELECT, STATE_MAIN_MENU,
    FRET_COLORS, COLOR_BG, COLOR_STAR, WHITE, GRAY,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect
from ui.song_select import INSTRUMENT_ICONS


GRADE_COLORS = {
    'SSS': (255, 215, 0),
    'SS':  (255, 200, 50),
    'S':   (255, 180, 80),
    'A':   (100, 255, 100),
    'B':   (100, 200, 255),
    'C':   (200, 200, 100),
    'D':   (180, 130, 60),
    'F':   (200, 50, 50),
}


def _star_unicode(stars: int) -> str:
    filled = min(stars, 5)
    return '⭐' * filled + '✩' * (5 - filled)


class ResultsScreen(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict, data: Dict):
        super().__init__(screen, config)
        self._chart   = data.get('chart')
        self._results: List[Dict] = data.get('results', [])
        self._t = time.monotonic()
        self._anim_done = False

        self._btn_retry = Button(
            rect=pygame.Rect(self.w // 2 - 200, self.h - 80, 180, 50),
            label="🔁  Jogar Novamente",
            color=(30, 80, 150),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_menu = Button(
            rect=pygame.Rect(self.w // 2 + 30, self.h - 80, 160, 50),
            label="📋  Seleção",
            color=(60, 60, 80),
            font_size=FONT_TINY_SIZE,
        )
        self._buttons = [self._btn_retry, self._btn_menu]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.transition_to(STATE_SONG_SELECT)
            elif event.key == pygame.K_ESCAPE:
                self.transition_to(STATE_MAIN_MENU)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._btn_retry.is_clicked(event):
                self.transition_to(STATE_SONG_SELECT)
            elif self._btn_menu.is_clicked(event):
                self.transition_to(STATE_SONG_SELECT)

    def update(self, dt: float) -> None:
        super().update(dt)

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self._draw_header()
        self._draw_results()
        self._btn_retry.draw(self.screen)
        self._btn_menu.draw(self.screen)

    def _draw_header(self) -> None:
        t = time.monotonic() - self._t
        draw_text(self.screen, "RESULTADO", self.w // 2, 30,
                  size=FONT_LARGE_SIZE, bold=True, color=COLOR_STAR,
                  center_x=True, shadow=True)
        if self._chart:
            meta = self._chart.metadata
            draw_text(self.screen, meta.display_name, self.w // 2, 80,
                      size=FONT_SMALL_SIZE, color=GRAY, center_x=True)

    def _draw_results(self) -> None:
        if not self._results:
            draw_text(self.screen, "Sem resultados.", self.w // 2, self.h // 2,
                      size=FONT_MEDIUM_SIZE, color=GRAY, center_x=True, center_y=True)
            return

        n = len(self._results)
        panel_w = min(340, (self.w - 80) // n)
        total_w = n * panel_w + (n - 1) * 20
        start_x = self.w // 2 - total_w // 2
        panel_y = 110
        panel_h = self.h - 210

        for i, res in enumerate(self._results):
            x = start_x + i * (panel_w + 20)
            self._draw_player_panel(x, panel_y, panel_w, panel_h, res, i)

    def _draw_player_panel(self, x: int, y: int, w: int, h: int, res: Dict, idx: int) -> None:
        t = time.monotonic() - self._t
        # Animação de entrada
        anim = min(1.0, t * 2 - idx * 0.3)
        if anim <= 0:
            return
        panel_y = int(y + (1 - anim) * 60)

        bg_alpha = int(220 * anim)
        draw_rounded_rect(self.screen, pygame.Rect(x, panel_y, w, h),
                          (28, 28, 48), radius=12, alpha=bg_alpha,
                          border_color=FRET_COLORS[idx % 5], border_width=2)

        cy = panel_y + 20
        inst = res.get('instrument', 'guitar')
        icon = INSTRUMENT_ICONS.get(inst, '?')
        draw_text(self.screen, f"P{idx+1}  {icon} {inst.capitalize()}",
                  x + w // 2, cy, size=FONT_SMALL_SIZE, color=WHITE,
                  center_x=True, bold=True)
        cy += 30

        diff = res.get('difficulty', '')
        draw_text(self.screen, diff.capitalize(), x + w // 2, cy,
                  size=FONT_TINY_SIZE, color=GRAY, center_x=True)
        cy += 30

        # Grade letter
        grade = res.get('grade', 'F')
        grade_color = GRADE_COLORS.get(grade, WHITE)
        pulse = 1.0 + 0.05 * math.sin(t * 4)
        draw_text(self.screen, grade, x + w // 2, cy,
                  size=int(64 * pulse), bold=True, color=grade_color, center_x=True)
        cy += 75

        # Stars
        stars = res.get('stars', 0)
        star_str = _star_unicode(stars)
        draw_text(self.screen, star_str, x + w // 2, cy,
                  size=22, color=COLOR_STAR, center_x=True)
        cy += 34

        # Score
        score = res.get('score', 0)
        draw_text(self.screen, f"{score:,}", x + w // 2, cy,
                  size=FONT_MEDIUM_SIZE, bold=True, color=WHITE, center_x=True)
        cy += 34

        # Stats
        acc = res.get('accuracy', 0.0)
        draw_text(self.screen, f"Precisão: {acc:.1f}%", x + w // 2, cy,
                  size=FONT_TINY_SIZE, color=GRAY, center_x=True)
        cy += 22

        hits  = res.get('notes_hit', 0)
        total = res.get('notes_total', 0)
        draw_text(self.screen, f"Notas: {hits}/{total}", x + w // 2, cy,
                  size=FONT_TINY_SIZE, color=GRAY, center_x=True)
        cy += 22

        streak = res.get('max_streak', 0)
        draw_text(self.screen, f"Maior streak: {streak}", x + w // 2, cy,
                  size=FONT_TINY_SIZE, color=GRAY, center_x=True)
        cy += 22

        if res.get('full_combo'):
            draw_text(self.screen, "✨ FULL COMBO!", x + w // 2, cy,
                      size=FONT_SMALL_SIZE, bold=True, color=COLOR_STAR, center_x=True)
