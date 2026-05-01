"""
Rock Band Local — Song Select Screen
"""
from __future__ import annotations
import os
import time
from typing import Dict, List, Optional, Tuple

import pygame

from game.chart_parser import Chart, discover_songs
from game.constants import (
    STATE_GAMEPLAY, STATE_MAIN_MENU,
    FRET_COLORS, WHITE, GRAY, DGRAY, COLOR_BG, COLOR_STAR,
    INSTRUMENTS, DIFFICULTIES,
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
    DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect, FontCache


INSTRUMENT_ICONS = {
    INSTRUMENT_GUITAR: "🎸",
    INSTRUMENT_BASS:   "🎵",
    INSTRUMENT_DRUMS:  "🥁",
    INSTRUMENT_VOCALS: "🎤",
}

DIFF_COLORS = {
    DIFF_EASY:   (50, 180, 50),
    DIFF_MEDIUM: (200, 160, 30),
    DIFF_HARD:   (200, 80, 30),
    DIFF_EXPERT: (180, 30, 30),
}


class SongSelectScreen(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict):
        super().__init__(screen, config)
        self._songs: List[Tuple[str, Chart]] = []
        self._selected_idx = 0
        self._scroll_offset = 0
        self._loading = True
        self._player_instruments = [INSTRUMENT_GUITAR]
        self._player_difficulties = [DIFF_MEDIUM]
        self._num_players = len(config.get('players', [{'instrument': INSTRUMENT_GUITAR}]))
        self._t = time.monotonic()

        # Painel direito — seleção de instrumento/dificuldade
        self._setting_player = 0   # qual jogador está configurando
        self._setting_field = 'instrument'   # 'instrument' ou 'difficulty'

        self._build_ui()

    def _build_ui(self) -> None:
        self._btn_play = Button(
            rect=pygame.Rect(self.w - 200, self.h - 80, 170, 50),
            label="▶  TOCAR",
            color=(30, 120, 30),
            hover_color=(50, 160, 50),
            font_size=FONT_SMALL_SIZE,
        )
        self._btn_back = Button(
            rect=pygame.Rect(20, self.h - 80, 130, 50),
            label="← Voltar",
            color=(60, 60, 80),
            font_size=FONT_SMALL_SIZE,
        )

    def on_enter(self) -> None:
        """Chamado quando a tela fica ativa — carrega músicas."""
        songs_path = self.config.get('songs_path', 'songs')
        self._songs = discover_songs(songs_path)
        self._loading = False
        if self._songs:
            self._selected_idx = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.transition_to(STATE_MAIN_MENU)
            elif event.key == pygame.K_DOWN:
                self._selected_idx = (self._selected_idx + 1) % max(1, len(self._songs))
            elif event.key == pygame.K_UP:
                self._selected_idx = (self._selected_idx - 1) % max(1, len(self._songs))
            elif event.key == pygame.K_RETURN and self._songs:
                self._launch_game()
            elif event.key == pygame.K_TAB:
                # Ciclar entre instrumento/dificuldade
                if self._setting_field == 'instrument':
                    self._setting_field = 'difficulty'
                else:
                    self._setting_field = 'instrument'
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._cycle_setting(1 if event.key == pygame.K_RIGHT else -1)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._btn_play.is_clicked(event) and self._songs:
                self._launch_game()
            elif self._btn_back.is_clicked(event):
                self.transition_to(STATE_MAIN_MENU)
            else:
                self._handle_list_click(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            self._selected_idx = max(0, min(len(self._songs) - 1,
                                            self._selected_idx - event.y))

    def _handle_list_click(self, pos: Tuple[int, int]) -> None:
        list_x, list_y = 20, 110
        item_h = 64
        for i, (folder, chart) in enumerate(self._songs):
            rect = pygame.Rect(list_x, list_y + i * item_h - self._scroll_offset, self.w // 2 - 40, item_h - 4)
            if rect.collidepoint(pos):
                if self._selected_idx == i:
                    self._launch_game()
                else:
                    self._selected_idx = i

    def _cycle_setting(self, direction: int) -> None:
        if self._setting_field == 'instrument':
            idx = INSTRUMENTS.index(self._player_instruments[self._setting_player])
            idx = (idx + direction) % len(INSTRUMENTS)
            self._player_instruments[self._setting_player] = INSTRUMENTS[idx]
        else:
            idx = DIFFICULTIES.index(self._player_difficulties[self._setting_player])
            idx = (idx + direction) % len(DIFFICULTIES)
            self._player_difficulties[self._setting_player] = DIFFICULTIES[idx]

    def _launch_game(self) -> None:
        if not self._songs:
            return
        folder, chart = self._songs[self._selected_idx]
        players = []
        for i in range(self._num_players):
            inst = self._player_instruments[i] if i < len(self._player_instruments) else INSTRUMENT_GUITAR
            diff = self._player_difficulties[i] if i < len(self._player_difficulties) else DIFF_MEDIUM
            players.append({'instrument': inst, 'difficulty': diff})
        self.transition_to(STATE_GAMEPLAY, {
            'folder': folder,
            'chart': chart,
            'players': players,
        })

    def update(self, dt: float) -> None:
        super().update(dt)
        # Scroll automático para manter selecionado visível
        item_h = 64
        visible_items = (self.h - 170) // item_h
        if self._selected_idx < self._scroll_offset // item_h:
            self._scroll_offset = self._selected_idx * item_h
        elif self._selected_idx >= self._scroll_offset // item_h + visible_items:
            self._scroll_offset = (self._selected_idx - visible_items + 1) * item_h
        self._scroll_offset = max(0, self._scroll_offset)

        # Num players sincronizado com config
        n = max(1, len(self.config.get('players', [{}])))
        while len(self._player_instruments) < n:
            self._player_instruments.append(INSTRUMENT_GUITAR)
            self._player_difficulties.append(DIFF_MEDIUM)

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self.draw_title("Selecionar Música", y=25)

        if self._loading:
            draw_text(self.screen, "Carregando músicas...", self.w // 2, self.h // 2,
                      center_x=True, center_y=True, size=FONT_MEDIUM_SIZE)
        elif not self._songs:
            self._draw_empty_state()
        else:
            self._draw_song_list()
            self._draw_details_panel()

        self._btn_play.draw(self.screen)
        self._btn_back.draw(self.screen)
        self._draw_player_settings()

    def _draw_empty_state(self) -> None:
        songs_path = self.config.get('songs_path', 'songs')
        draw_text(self.screen, "Nenhuma música encontrada.", self.w // 2, self.h // 2 - 30,
                  size=FONT_MEDIUM_SIZE, color=GRAY, center_x=True, center_y=True)
        draw_text(self.screen, f"Coloque pastas com notes.chart em: {os.path.abspath(songs_path)}",
                  self.w // 2, self.h // 2 + 10, size=FONT_TINY_SIZE, color=GRAY, center_x=True)
        draw_text(self.screen, "Ou use 🌐 Rhythmverse para baixar músicas!",
                  self.w // 2, self.h // 2 + 40, size=FONT_SMALL_SIZE, color=(100, 200, 255), center_x=True)

    def _draw_song_list(self) -> None:
        list_x, list_y = 20, 110
        item_h = 64
        list_w = self.w // 2 - 40
        visible = (self.h - 160) // item_h

        clip = pygame.Rect(list_x - 4, list_y - 4, list_w + 8, self.h - 180)
        self.screen.set_clip(clip)

        for i, (folder, chart) in enumerate(self._songs):
            y = list_y + i * item_h - self._scroll_offset
            if y + item_h < list_y or y > list_y + (visible * item_h):
                continue

            selected = (i == self._selected_idx)
            bg_color = (40, 40, 70) if selected else (28, 28, 45)
            border   = FRET_COLORS[1] if selected else None
            rect = pygame.Rect(list_x, y, list_w, item_h - 4)
            draw_rounded_rect(self.screen, rect, bg_color, radius=8,
                              border_color=border, border_width=2)

            # Título e artista
            meta = chart.metadata
            draw_text(self.screen, meta.name, list_x + 12, y + 8,
                      size=FONT_SMALL_SIZE, bold=True, color=WHITE)
            draw_text(self.screen, meta.artist, list_x + 12, y + 32,
                      size=FONT_TINY_SIZE, color=GRAY)

            # Chips de instrumento disponível
            cx = list_x + list_w - 10
            cy = y + item_h // 2 - 8
            for inst in (INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS):
                if chart.get_notes(inst, DIFF_EXPERT) or chart.get_notes(inst, DIFF_MEDIUM):
                    icon = INSTRUMENT_ICONS[inst]
                    surf = FontCache.get(14).render(icon, True, GRAY)
                    self.screen.blit(surf, (cx - surf.get_width(), cy))
                    cx -= surf.get_width() + 4

        self.screen.set_clip(None)

        # Scrollbar
        total_h = len(self._songs) * item_h
        if total_h > self.h - 160:
            bar_h = max(30, int((self.h - 160) / total_h * (self.h - 160)))
            bar_y = list_y + int(self._scroll_offset / total_h * (self.h - 160))
            pygame.draw.rect(self.screen, GRAY,
                             (list_x + list_w + 6, bar_y, 4, bar_h), border_radius=2)

    def _draw_details_panel(self) -> None:
        if not self._songs:
            return
        folder, chart = self._songs[self._selected_idx]
        meta = chart.metadata
        panel_x = self.w // 2 + 10
        panel_y = 110
        panel_w = self.w - panel_x - 20
        panel_h = self.h - 160

        draw_rounded_rect(self.screen, pygame.Rect(panel_x, panel_y, panel_w, panel_h),
                          (28, 28, 45), radius=10)

        y = panel_y + 16
        draw_text(self.screen, meta.name, panel_x + panel_w // 2, y,
                  size=FONT_MEDIUM_SIZE, bold=True, color=WHITE, center_x=True)
        y += 36

        if meta.artist:
            draw_text(self.screen, meta.artist, panel_x + panel_w // 2, y,
                      size=FONT_SMALL_SIZE, color=GRAY, center_x=True)
            y += 26

        if meta.album:
            draw_text(self.screen, meta.album, panel_x + panel_w // 2, y,
                      size=FONT_TINY_SIZE, color=(80, 80, 100), center_x=True)
            y += 22

        pygame.draw.line(self.screen, (50, 50, 70), (panel_x + 10, y), (panel_x + panel_w - 10, y))
        y += 14

        if meta.charter:
            draw_text(self.screen, f"Chart: {meta.charter}", panel_x + 12, y,
                      size=FONT_TINY_SIZE, color=(100, 200, 100))
            y += 22

        if meta.genre:
            draw_text(self.screen, f"Gênero: {meta.genre}", panel_x + 12, y,
                      size=FONT_TINY_SIZE, color=(150, 150, 200))
            y += 22

        y += 10
        # Instrumentos disponíveis
        draw_text(self.screen, "Instrumentos disponíveis:", panel_x + 12, y,
                  size=FONT_TINY_SIZE, color=GRAY)
        y += 22

        for inst in INSTRUMENTS:
            available_diffs = [d for d in DIFFICULTIES if chart.get_notes(inst, d)]
            if not available_diffs:
                continue
            icon = INSTRUMENT_ICONS.get(inst, '?')
            diff_str = " / ".join(d.capitalize() for d in available_diffs)
            draw_text(self.screen, f"  {icon} {inst.capitalize()}: {diff_str}",
                      panel_x + 12, y, size=FONT_TINY_SIZE, color=WHITE)
            y += 20

        # Áudio disponível
        if meta.audio_streams:
            y += 6
            stems = ", ".join(sorted(meta.audio_streams.keys()))
            draw_text(self.screen, f"Áudio: {stems}", panel_x + 12, y,
                      size=FONT_TINY_SIZE, color=(80, 160, 80))

    def _draw_player_settings(self) -> None:
        n = len(self.config.get('players', [{}]))
        base_y = self.h - 75
        x = 170

        for i in range(min(n, 4)):
            inst = self._player_instruments[i] if i < len(self._player_instruments) else INSTRUMENT_GUITAR
            diff = self._player_difficulties[i] if i < len(self._player_difficulties) else DIFF_MEDIUM
            icon = INSTRUMENT_ICONS.get(inst, '?')
            diff_color = DIFF_COLORS.get(diff, GRAY)

            label = f"P{i+1}: {icon}  {diff.capitalize()}"
            color = (35, 35, 55) if self._setting_player != i else (50, 50, 80)
            rect  = pygame.Rect(x + i * 160, base_y, 150, 44)
            draw_rounded_rect(self.screen, rect, color, radius=8,
                              border_color=diff_color, border_width=1)
            draw_text(self.screen, label, rect.centerx, rect.centery,
                      size=FONT_TINY_SIZE, color=WHITE, center_x=True, center_y=True)

        draw_text(self.screen, "TAB: trocar campo   ← →: mudar valor",
                  self.w // 2, self.h - 16, size=FONT_TINY_SIZE,
                  color=(60, 60, 80), center_x=True)
