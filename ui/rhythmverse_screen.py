"""
Rock Band Local — Rhythmverse Browser Screen
Navega e baixa músicas de rhythmverse.co
"""
from __future__ import annotations
import threading
import time
from typing import Dict, List, Optional

import pygame

from network.rhythmverse_client import RhythmverseClient, RVSong, SearchResult
from game.constants import (
    STATE_MAIN_MENU, STATE_SONG_SELECT,
    COLOR_BG, WHITE, GRAY, DGRAY, COLOR_STAR,
    FRET_COLORS,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect


class RhythmverseScreen(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict):
        super().__init__(screen, config)
        self._client = RhythmverseClient(config)
        self._songs: List[RVSong] = []
        self._selected_idx = 0
        self._scroll_offset = 0
        self._loading = False
        self._status_msg = ""
        self._status_color = GRAY
        self._query = ""
        self._page = 1
        self._total_pages = 1
        self._download_progress: Dict[str, float] = {}  # song_id -> 0.0-1.0
        self._search_input_active = False
        self._input_text = ""

        self._btn_search = Button(
            pygame.Rect(self.w - 160, 70, 140, 38),
            "🔍 Buscar",
            color=(30, 80, 150),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_download = Button(
            pygame.Rect(self.w - 170, self.h - 80, 150, 50),
            "⬇️  Baixar",
            color=(30, 120, 30),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_back = Button(
            pygame.Rect(20, self.h - 80, 130, 50),
            "← Voltar",
            color=(60, 60, 80),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_prev = Button(
            pygame.Rect(self.w // 2 - 130, self.h - 78, 110, 44),
            "◀ Anterior",
            color=(50, 50, 70),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_next = Button(
            pygame.Rect(self.w // 2 + 20, self.h - 78, 110, 44),
            "Próxima ▶",
            color=(50, 50, 70),
            font_size=FONT_TINY_SIZE,
        )
        self._buttons = [self._btn_search, self._btn_download, self._btn_back,
                         self._btn_prev, self._btn_next]
        self._search_rect = pygame.Rect(20, 70, self.w - 200, 38)

    def on_enter(self) -> None:
        self._load_featured()

    def _load_featured(self) -> None:
        self._loading = True
        self._status_msg = "Carregando destaques..."
        self._status_color = (100, 180, 255)

        def task():
            try:
                result = self._client.search(self._query, self._page)
                self._songs = result.songs
                self._total_pages = result.total_pages
                self._status_msg = f"{len(self._songs)} músicas encontradas" + (
                    f" (pág. {self._page}/{self._total_pages})" if self._total_pages > 1 else ""
                )
                self._status_color = (100, 255, 100)
            except Exception as e:
                self._songs = []
                self._status_msg = f"Erro: {e}"
                self._status_color = (255, 80, 80)
            finally:
                self._loading = False

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_search(self) -> None:
        self._query = self._input_text
        self._page = 1
        self._selected_idx = 0
        self._scroll_offset = 0
        self._load_featured()

    def _download_selected(self) -> None:
        if not self._songs or self._selected_idx >= len(self._songs):
            return
        song = self._songs[self._selected_idx]
        if song.id in self._download_progress:
            return

        self._download_progress[song.id] = 0.0
        self._status_msg = f"Baixando: {song.title}..."
        self._status_color = (255, 200, 50)

        def task():
            def progress_cb(p: float):
                self._download_progress[song.id] = p

            result = self._client.download_song(song, progress_cb=progress_cb)
            if result:
                self._status_msg = f"✅ Baixado: {song.title}"
                self._status_color = (100, 255, 100)
            else:
                self._status_msg = f"❌ Falha ao baixar: {song.title}"
                self._status_color = (255, 80, 80)
            del self._download_progress[song.id]

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.transition_to(STATE_MAIN_MENU)
            elif self._search_input_active:
                if event.key == pygame.K_RETURN:
                    self._search_input_active = False
                    self._do_search()
                elif event.key == pygame.K_BACKSPACE:
                    self._input_text = self._input_text[:-1]
                else:
                    if event.unicode.isprintable():
                        self._input_text += event.unicode
            else:
                if event.key == pygame.K_DOWN:
                    self._selected_idx = min(self._selected_idx + 1, len(self._songs) - 1)
                elif event.key == pygame.K_UP:
                    self._selected_idx = max(self._selected_idx - 1, 0)
                elif event.key == pygame.K_RETURN and self._songs:
                    self._download_selected()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._search_rect.collidepoint(event.pos):
                self._search_input_active = True
            else:
                self._search_input_active = False

            if self._btn_search.is_clicked(event):
                self._do_search()
            elif self._btn_download.is_clicked(event):
                self._download_selected()
            elif self._btn_back.is_clicked(event):
                self.transition_to(STATE_MAIN_MENU)
            elif self._btn_prev.is_clicked(event) and self._page > 1:
                self._page -= 1
                self._load_featured()
            elif self._btn_next.is_clicked(event) and self._page < self._total_pages:
                self._page += 1
                self._load_featured()
            else:
                self._handle_list_click(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            self._selected_idx = max(0, min(len(self._songs) - 1,
                                            self._selected_idx - event.y))

    def _handle_list_click(self, pos) -> None:
        list_x, list_y = 20, 120
        item_h = 62
        for i in range(len(self._songs)):
            y = list_y + i * item_h - self._scroll_offset
            rect = pygame.Rect(list_x, y, self.w - 320, item_h - 4)
            if rect.collidepoint(pos):
                self._selected_idx = i

    def update(self, dt: float) -> None:
        super().update(dt)
        # Scroll
        item_h = 62
        visible = (self.h - 200) // item_h
        if self._selected_idx < self._scroll_offset // item_h:
            self._scroll_offset = self._selected_idx * item_h
        elif self._selected_idx >= self._scroll_offset // item_h + visible:
            self._scroll_offset = (self._selected_idx - visible + 1) * item_h
        self._scroll_offset = max(0, self._scroll_offset)

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self.draw_title("🌐  Rhythmverse", y=22)

        # Campo de busca
        border_color = (80, 120, 200) if self._search_input_active else (50, 50, 70)
        draw_rounded_rect(self.screen, self._search_rect, (25, 25, 42), radius=8,
                          border_color=border_color, border_width=2)
        display_text = self._input_text + ("│" if self._search_input_active else "")
        placeholder = display_text or "Buscar por título, artista, charter..."
        color = WHITE if self._input_text else (80, 80, 100)
        draw_text(self.screen, placeholder, self._search_rect.x + 10, self._search_rect.y + 10,
                  size=FONT_TINY_SIZE, color=color)

        self._btn_search.draw(self.screen)

        # Status
        draw_text(self.screen, self._status_msg, 20, 116,
                  size=FONT_TINY_SIZE, color=self._status_color)

        # Lista
        if self._loading:
            t = time.monotonic()
            dots = '.' * (int(t * 3) % 4)
            draw_text(self.screen, f"Carregando{dots}", self.w // 2, self.h // 2,
                      size=FONT_MEDIUM_SIZE, color=GRAY, center_x=True, center_y=True)
        else:
            self._draw_song_list()
            if self._songs:
                self._draw_details_panel()

        # Botões
        self._btn_download.draw(self.screen)
        self._btn_back.draw(self.screen)
        if self._total_pages > 1:
            self._btn_prev.draw(self.screen)
            self._btn_next.draw(self.screen)
            draw_text(self.screen, f"Pág. {self._page}/{self._total_pages}",
                      self.w // 2, self.h - 60,
                      size=FONT_TINY_SIZE, color=GRAY, center_x=True)

    def _draw_song_list(self) -> None:
        list_x, list_y = 20, 128
        item_h = 62
        list_w = self.w - 320

        clip = pygame.Rect(list_x - 4, list_y - 4, list_w + 8, self.h - 190)
        self.screen.set_clip(clip)

        for i, song in enumerate(self._songs):
            y = list_y + i * item_h - self._scroll_offset
            if y + item_h < list_y or y > list_y + self.h - 190:
                continue

            selected = (i == self._selected_idx)
            bg = (42, 42, 68) if selected else (26, 26, 42)
            border = FRET_COLORS[1] if selected else None
            rect = pygame.Rect(list_x, y, list_w, item_h - 4)
            draw_rounded_rect(self.screen, rect, bg, radius=8,
                              border_color=border, border_width=2)

            draw_text(self.screen, song.title, list_x + 10, y + 8,
                      size=FONT_SMALL_SIZE, bold=True, color=WHITE)
            draw_text(self.screen, song.artist or "Artista desconhecido",
                      list_x + 10, y + 32, size=FONT_TINY_SIZE, color=GRAY)

            # Progresso de download
            if song.id in self._download_progress:
                prog = self._download_progress[song.id]
                bar_w = int((list_w - 20) * prog)
                pygame.draw.rect(self.screen, (30, 140, 30),
                                 (list_x + 10, y + item_h - 10, bar_w, 4), border_radius=2)

        self.screen.set_clip(None)

    def _draw_details_panel(self) -> None:
        if not self._songs or self._selected_idx >= len(self._songs):
            return
        song = self._songs[self._selected_idx]
        px = self.w - 295
        py = 128
        pw = 280
        ph = self.h - 210

        draw_rounded_rect(self.screen, pygame.Rect(px, py, pw, ph), (28, 28, 46), radius=10)

        y = py + 16
        draw_text(self.screen, song.title, px + pw // 2, y,
                  size=FONT_SMALL_SIZE, bold=True, color=WHITE, center_x=True)
        y += 28

        if song.artist:
            draw_text(self.screen, song.artist, px + pw // 2, y,
                      size=FONT_TINY_SIZE, color=GRAY, center_x=True)
            y += 22

        pygame.draw.line(self.screen, (50, 50, 70), (px + 10, y), (px + pw - 10, y))
        y += 14

        if song.charter:
            draw_text(self.screen, f"Charter: {song.charter}",
                      px + 12, y, size=FONT_TINY_SIZE, color=(100, 200, 100))
            y += 20

        if song.genre:
            draw_text(self.screen, f"Gênero: {song.genre}",
                      px + 12, y, size=FONT_TINY_SIZE, color=(150, 150, 200))
            y += 20

        y += 10
        insts = []
        if song.has_guitar: insts.append("🎸 Guitarra")
        if song.has_bass:   insts.append("🎵 Baixo")
        if song.has_drums:  insts.append("🥁 Bateria")
        if song.has_vocals: insts.append("🎤 Vocal")
        for inst in insts:
            draw_text(self.screen, inst, px + 12, y,
                      size=FONT_TINY_SIZE, color=WHITE)
            y += 20

        if song.id in self._download_progress:
            prog = self._download_progress[song.id]
            draw_text(self.screen, f"Baixando... {prog * 100:.0f}%",
                      px + pw // 2, y + 20, size=FONT_TINY_SIZE,
                      color=(255, 200, 50), center_x=True)
