"""
Rock Band Local — Download Music Screen (Rhythmverse Browser)
Navega e baixa músicas de rhythmverse.co usando a API JSON real.
"""
from __future__ import annotations
import threading
import time
from typing import Dict, List, Optional

import pygame

from network.rhythmverse_client import RhythmverseClient, RVSong, SearchResult, GAMEFORMATS
from game.constants import (
    STATE_MAIN_MENU,
    COLOR_BG, WHITE, GRAY, DGRAY, COLOR_STAR,
    FRET_COLORS,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect


# Formato exibido nos botões de filtro rápido
FILTER_FORMATS = [
    ("Todos",   "all"),
    ("CH",      "chm"),
    ("YARG",    "yarg"),
    ("RB3",     "rb3"),
    ("PS",      "ps"),
    ("WTDE",    "wtde"),
]

# Cores por gameformat (para o badge)
FORMAT_COLORS: Dict[str, tuple] = {
    "chm":     (50, 160, 80),
    "ch":      (50, 160, 80),
    "yarg":    (80, 140, 220),
    "rb3":     (200, 60, 60),
    "rb3xbox": (200, 60, 60),
    "rb3wii":  (180, 80, 60),
    "rb3ps3":  (180, 60, 80),
    "wtde":    (180, 100, 40),
    "tbrb":    (160, 80, 180),
    "ps":      (60, 150, 180),
}


class RhythmverseScreen(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict):
        super().__init__(screen, config)
        self._client  = RhythmverseClient(config)
        self._songs: List[RVSong] = []
        self._selected_idx = 0
        self._scroll_offset = 0
        self._loading = False
        self._status_msg = ""
        self._status_color = GRAY
        self._query = ""
        self._page = 1
        self._total_pages = 1
        self._total_songs = 0
        self._gameformat = "all"
        self._download_progress: Dict[str, float] = {}
        self._search_input_active = False
        self._input_text = ""
        self._debounce_timer = 0.0
        self._last_query_typed = ""

        # Layout
        self._top_bar_h = 60
        self._filter_bar_h = 42
        self._status_bar_h = 24
        self._bottom_bar_h = 60
        self._list_x = 20
        self._detail_w = 285
        self._item_h = 64

        # Search bar
        self._search_rect = pygame.Rect(
            self._list_x, self._top_bar_h + 8,
            self.w - self._detail_w - self._list_x - 20 - 120, 36
        )

        # Botão busca
        self._btn_search = Button(
            pygame.Rect(self._search_rect.right + 8, self._top_bar_h + 8, 106, 36),
            "🔍  Buscar",
            color=(30, 80, 160),
            font_size=FONT_TINY_SIZE,
        )

        # Botões filtro de formato
        filter_y = self._top_bar_h + self._filter_bar_h + 4
        fw = 68
        self._filter_btns: List[tuple] = []  # (Button, fmt)
        for i, (label, fmt) in enumerate(FILTER_FORMATS):
            bx = self._list_x + i * (fw + 6)
            btn = Button(
                pygame.Rect(bx, filter_y - self._filter_bar_h + 4, fw, 32),
                label,
                color=(40, 60, 40) if fmt == "all" else (30, 45, 75),
                font_size=FONT_TINY_SIZE,
            )
            self._filter_btns.append((btn, fmt))

        # Bottom
        boty = self.h - self._bottom_bar_h + 8
        self._btn_back = Button(
            pygame.Rect(self._list_x, boty, 120, 42),
            "← Voltar",
            color=(55, 55, 75),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_download = Button(
            pygame.Rect(self.w - self._detail_w, boty, self._detail_w - 10, 42),
            "⬇  Baixar",
            color=(25, 120, 45),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_prev = Button(
            pygame.Rect(self.w // 2 - 140, boty, 120, 42),
            "◀ Anterior",
            color=(45, 45, 65),
            font_size=FONT_TINY_SIZE,
        )
        self._btn_next = Button(
            pygame.Rect(self.w // 2 + 20, boty, 120, 42),
            "Próxima ▶",
            color=(45, 45, 65),
            font_size=FONT_TINY_SIZE,
        )
        # Retry button shown on network error
        self._btn_retry = Button(
            pygame.Rect(self.w // 2 - 90, self.h // 2 + 20, 180, 44),
            "🔄  Tentar Novamente",
            color=(60, 40, 100),
            font_size=FONT_TINY_SIZE,
        )
        self._has_error = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._do_load()

    # ── Loading ────────────────────────────────────────────────────────────────

    def _do_load(self) -> None:
        self._loading = True
        self._has_error = False
        self._status_msg = "Conectando a Rhythmverse..."
        self._status_color = (100, 180, 255)
        q = self._query

        def task():
            try:
                result = self._client.search(
                    query=q,
                    page=self._page,
                    gameformat=self._gameformat,
                )
                self._songs = result.songs
                self._total_pages = result.total_pages
                self._total_songs = result.total_songs
                self._has_error = False
                if result.total_songs == 0 and not q:
                    # Empty result without query — likely a network issue
                    self._has_error = True
                    self._status_msg = "❌ Sem conexão com Rhythmverse. Verifique a internet."
                    self._status_color = (255, 100, 80)
                elif q:
                    self._status_msg = f'\U0001f50d {result.total_songs:,} resultados para "{q}"'
                    self._status_color = (100, 220, 120)
                else:
                    self._status_msg = f"📂 {result.total_songs:,} músicas — pág. {self._page}/{self._total_pages}"
                    self._status_color = (100, 220, 120)
            except Exception as e:
                self._songs = []
                self._has_error = True
                short_err = str(e)[:80]
                self._status_msg = f"❌ Erro de rede: {short_err}"
                self._status_color = (255, 80, 80)
            finally:
                self._loading = False

        threading.Thread(target=task, daemon=True).start()

    def _start_search(self) -> None:
        self._query = self._input_text.strip()
        self._page = 1
        self._selected_idx = 0
        self._scroll_offset = 0
        self._do_load()

    def _download_selected(self) -> None:
        if not self._songs or self._selected_idx >= len(self._songs):
            return
        song = self._songs[self._selected_idx]
        if song.id in self._download_progress:
            return

        if not song.has_direct_download:
            self._status_msg = f"⚠ Sem download direto — abra: {song.download_page_url}"
            self._status_color = (255, 200, 60)
            return

        self._download_progress[song.id] = 0.0
        self._status_msg = f"⬇ Baixando: {song.title}..."
        self._status_color = (255, 200, 50)

        def task():
            def cb(p: float):
                self._download_progress[song.id] = p

            result = self._client.download_song(song, progress_cb=cb)
            if result:
                self._status_msg = f"✅ Baixado: {song.display_name}"
                self._status_color = (100, 255, 120)
            else:
                self._status_msg = f"❌ Falha: {song.title}"
                self._status_color = (255, 80, 80)
            self._download_progress.pop(song.id, None)

        threading.Thread(target=task, daemon=True).start()

    def _set_gameformat(self, fmt: str) -> None:
        if fmt == self._gameformat:
            return
        self._gameformat = fmt
        self._page = 1
        self._selected_idx = 0
        self._scroll_offset = 0
        self._do_load()

    # ── Events ─────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.transition_to(STATE_MAIN_MENU)
            elif self._search_input_active:
                if event.key == pygame.K_RETURN:
                    self._search_input_active = False
                    self._start_search()
                elif event.key == pygame.K_BACKSPACE:
                    self._input_text = self._input_text[:-1]
                elif event.unicode.isprintable():
                    self._input_text += event.unicode
            else:
                if event.key == pygame.K_r and self._has_error:
                    self._do_load()
                elif event.key == pygame.K_DOWN:
                    self._selected_idx = min(self._selected_idx + 1, len(self._songs) - 1)
                elif event.key == pygame.K_UP:
                    self._selected_idx = max(self._selected_idx - 1, 0)
                elif event.key == pygame.K_RETURN and self._songs:
                    self._download_selected()
                elif event.key == pygame.K_RIGHT and self._page < self._total_pages:
                    self._page += 1
                    self._do_load()
                elif event.key == pygame.K_LEFT and self._page > 1:
                    self._page -= 1
                    self._do_load()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self._search_rect.collidepoint(event.pos):
                self._search_input_active = True
            else:
                self._search_input_active = False

            if self._btn_retry.is_clicked(event) and self._has_error:
                self._do_load()
            elif self._btn_search.is_clicked(event):
                self._start_search()
            elif self._btn_download.is_clicked(event):
                self._download_selected()
            elif self._btn_back.is_clicked(event):
                self.transition_to(STATE_MAIN_MENU)
            elif self._btn_prev.is_clicked(event) and self._page > 1:
                self._page -= 1
                self._do_load()
            elif self._btn_next.is_clicked(event) and self._page < self._total_pages:
                self._page += 1
                self._do_load()
            else:
                for btn, fmt in self._filter_btns:
                    if btn.is_clicked(event):
                        self._set_gameformat(fmt)
                        break
                else:
                    self._handle_list_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            self._selected_idx = max(0, min(
                len(self._songs) - 1,
                self._selected_idx - event.y
            ))

    def _handle_list_click(self, pos) -> None:
        list_top = self._list_top()
        for i in range(len(self._songs)):
            y = list_top + i * self._item_h - self._scroll_offset
            rect = pygame.Rect(self._list_x, y, self._list_w(), self._item_h - 4)
            if rect.collidepoint(pos):
                self._selected_idx = i
                break

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        super().update(dt)
        # Auto-scroll to keep selected item visible
        visible = self._visible_items()
        first = self._scroll_offset // self._item_h
        if self._selected_idx < first:
            self._scroll_offset = self._selected_idx * self._item_h
        elif self._selected_idx >= first + visible:
            self._scroll_offset = (self._selected_idx - visible + 1) * self._item_h
        self._scroll_offset = max(0, self._scroll_offset)

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self.draw_title("📥  Download Music  —  Rhythmverse", y=18)

        self._draw_search_bar()
        self._draw_format_filter()
        self._draw_status_bar()
        self._draw_song_list()
        self._draw_detail_panel()
        self._draw_bottom_bar()

    def _draw_search_bar(self) -> None:
        border_c = (80, 130, 220) if self._search_input_active else (50, 50, 72)
        draw_rounded_rect(self.screen, self._search_rect, (22, 22, 38),
                          radius=8, border_color=border_c, border_width=2)
        text = self._input_text + ("│" if self._search_input_active else "")
        placeholder = text if text else "Buscar por artista, título, charter..."
        color = WHITE if self._input_text else (70, 70, 95)
        draw_text(self.screen, placeholder,
                  self._search_rect.x + 10, self._search_rect.y + 9,
                  size=FONT_TINY_SIZE, color=color)
        self._btn_search.draw(self.screen)

    def _draw_format_filter(self) -> None:
        for btn, fmt in self._filter_btns:
            active = (fmt == self._gameformat)
            c = FORMAT_COLORS.get(fmt, (40, 60, 40)) if active else (30, 35, 55)
            # Temporariamente alterar a cor do botão
            btn.color = c
            btn.draw(self.screen)
            if active:
                r = btn.rect
                pygame.draw.rect(self.screen, (200, 220, 255),
                                 (r.x, r.bottom - 3, r.width, 3), border_radius=2)

    def _draw_status_bar(self) -> None:
        sy = self._top_bar_h + self._filter_bar_h + 6
        if self._loading:
            t = time.monotonic()
            dots = '.' * (int(t * 3) % 4)
            draw_text(self.screen, f"Carregando{dots}", self._list_x + 4, sy,
                      size=FONT_TINY_SIZE, color=(100, 180, 255))
        else:
            draw_text(self.screen, self._status_msg, self._list_x + 4, sy,
                      size=FONT_TINY_SIZE, color=self._status_color)

    def _draw_song_list(self) -> None:
        cx = self.w // 2 - self._detail_w // 2

        if self._loading:
            t = time.monotonic()
            dots = "●" * (int(t * 2) % 4 + 1)
            draw_text(self.screen, f"Conectando a Rhythmverse  {dots}", cx, self.h // 2 - 20,
                      size=FONT_MEDIUM_SIZE, color=(100, 180, 255), center_x=True, center_y=True)
            return

        if self._has_error or not self._songs:
            if self._has_error:
                draw_text(self.screen, "Sem conexão com Rhythmverse",
                          cx, self.h // 2 - 40,
                          size=FONT_SMALL_SIZE, color=(255, 100, 80), center_x=True, center_y=True)
                draw_text(self.screen, "Verifique sua internet e tente novamente.",
                          cx, self.h // 2 - 14,
                          size=FONT_TINY_SIZE, color=GRAY, center_x=True, center_y=True)
                # Reposition retry button centered in list area
                self._btn_retry.rect.centerx = cx
                self._btn_retry.rect.y = self.h // 2 + 12
                self._btn_retry.draw(self.screen)
            else:
                draw_text(self.screen, "Nenhuma música encontrada",
                          cx, self.h // 2,
                          size=FONT_SMALL_SIZE, color=GRAY, center_x=True, center_y=True)
            return

        list_top = self._list_top()
        lw = self._list_w()
        clip = pygame.Rect(self._list_x - 2, list_top - 2, lw + 4, self._list_height())
        self.screen.set_clip(clip)

        for i, song in enumerate(self._songs):
            y = list_top + i * self._item_h - self._scroll_offset
            if y + self._item_h < list_top or y > list_top + self._list_height():
                continue
            self._draw_song_card(i, song, y, lw)

        self.screen.set_clip(None)

    def _draw_song_card(self, idx: int, song: RVSong, y: int, lw: int) -> None:
        selected = (idx == self._selected_idx)
        bg = (42, 42, 68) if selected else (24, 24, 38)
        border_c = FRET_COLORS[1] if selected else None
        rect = pygame.Rect(self._list_x, y, lw, self._item_h - 4)
        draw_rounded_rect(self.screen, rect, bg, radius=8,
                          border_color=border_c, border_width=2 if selected else 0)

        # Badge de gameformat
        fmt_color = FORMAT_COLORS.get(song.gameformat, (70, 70, 90))
        badge_w = 52
        badge_rect = pygame.Rect(rect.right - badge_w - 8, y + 14, badge_w, 20)
        draw_rounded_rect(self.screen, badge_rect, fmt_color, radius=5)
        draw_text(self.screen, song.gameformat.upper()[:6],
                  badge_rect.centerx, badge_rect.centery,
                  size=8, color=WHITE, center_x=True, center_y=True)

        # Download indicator
        dl_icon = "⬇" if song.has_direct_download else "🔗"
        draw_text(self.screen, dl_icon, rect.right - badge_w - 28, y + 14,
                  size=FONT_TINY_SIZE, color=(120, 220, 120) if song.has_direct_download else (200, 180, 80))

        # Título e artista
        title_max = lw - badge_w - 60
        draw_text(self.screen, _trim(song.title, 42),
                  self._list_x + 10, y + 8,
                  size=FONT_SMALL_SIZE, bold=True, color=WHITE)
        info = song.artist or "Artista desconhecido"
        if song.year and song.year > 0:
            info += f"  ({song.year})"
        if song.duration_sec > 0:
            m, s = divmod(song.duration_sec, 60)
            info += f"  {m}:{s:02d}"
        draw_text(self.screen, _trim(info, 55),
                  self._list_x + 10, y + 34,
                  size=FONT_TINY_SIZE, color=GRAY)

        # Barra de progresso de download
        if song.id in self._download_progress:
            prog = self._download_progress[song.id]
            bw = int((lw - 20) * prog)
            pygame.draw.rect(self.screen, (30, 170, 50),
                             (self._list_x + 10, y + self._item_h - 10, bw, 4),
                             border_radius=2)

    def _draw_detail_panel(self) -> None:
        px = self.w - self._detail_w + 2
        py = self._list_top()
        pw = self._detail_w - 8
        ph = self._list_height()
        draw_rounded_rect(self.screen, pygame.Rect(px, py, pw, ph), (22, 22, 38), radius=10)

        if not self._songs or self._selected_idx >= len(self._songs):
            draw_text(self.screen, "Selecione uma música",
                      px + pw // 2, py + ph // 2,
                      size=FONT_TINY_SIZE, color=DGRAY, center_x=True, center_y=True)
            return

        song = self._songs[self._selected_idx]
        y = py + 16
        cx = px + pw // 2

        # Título
        for line in _wrap(song.title, 22):
            draw_text(self.screen, line, cx, y, size=FONT_SMALL_SIZE,
                      bold=True, color=WHITE, center_x=True)
            y += 22

        # Artista
        if song.artist:
            draw_text(self.screen, song.artist, cx, y,
                      size=FONT_TINY_SIZE, color=(160, 200, 255), center_x=True)
            y += 20

        pygame.draw.line(self.screen, (45, 45, 65), (px + 10, y + 4), (px + pw - 10, y + 4))
        y += 16

        def info_row(label: str, value: str, color=(180, 180, 200)):
            nonlocal y
            if value:
                draw_text(self.screen, f"{label}: {value}", px + 10, y,
                          size=FONT_TINY_SIZE, color=color)
                y += 18

        # Metadata
        fmt_name = GAMEFORMATS.get(song.gameformat, song.gameformat)
        info_row("🎮", fmt_name, FORMAT_COLORS.get(song.gameformat, (180, 180, 200)))
        if song.charter:
            info_row("✍", _trim(song.charter, 22), (120, 220, 120))
        if song.genre:
            info_row("🎵", song.genre, (150, 150, 210))
        if song.year > 0:
            info_row("📅", str(song.year), (200, 170, 120))
        if song.album:
            info_row("💿", _trim(song.album, 22), (170, 150, 200))
        if song.audio_type:
            info_row("🔊", song.audio_type, (100, 180, 200))
        if song.downloads > 0:
            info_row("⬇", f"{song.downloads:,}×", (120, 180, 255))

        y += 6
        pygame.draw.line(self.screen, (45, 45, 65), (px + 10, y), (px + pw - 10, y))
        y += 10

        # Instrumentos e dificuldades
        inst_data = [
            ("🎸", "Guitarra", song.has_guitar, song.diff_guitar),
            ("🎵", "Baixo",    song.has_bass,   song.diff_bass),
            ("🥁", "Bateria",  song.has_drums,  song.diff_drums),
            ("🎤", "Vocal",    song.has_vocals, song.diff_vocals),
            ("🎹", "Keys",     song.has_keys,   song.diff_keys),
        ]
        for icon, name, present, diff in inst_data:
            if present:
                diff_str = _diff_stars(diff) if diff >= 0 else ""
                draw_text(self.screen, f"{icon} {name}  {diff_str}",
                          px + 10, y, size=FONT_TINY_SIZE, color=WHITE)
                y += 18

        # Completeness bar
        if song.completeness > 0:
            y += 6
            draw_text(self.screen, "Qualidade:", px + 10, y,
                      size=FONT_TINY_SIZE, color=GRAY)
            y += 18
            bar_total = pw - 20
            bar_filled = int(bar_total * song.completeness / 6)
            pygame.draw.rect(self.screen, (40, 40, 60),
                             (px + 10, y, bar_total, 8), border_radius=4)
            c = (50, 200, 80) if song.completeness >= 5 else (
                (200, 200, 50) if song.completeness >= 3 else (200, 80, 50))
            pygame.draw.rect(self.screen, c,
                             (px + 10, y, bar_filled, 8), border_radius=4)
            y += 18

        # Status de download
        y += 6
        if song.id in self._download_progress:
            prog = self._download_progress[song.id]
            draw_text(self.screen, f"⬇ Baixando {prog * 100:.0f}%...",
                      cx, y, size=FONT_TINY_SIZE, color=(255, 210, 60), center_x=True)
        elif song.has_direct_download:
            draw_text(self.screen, "✅ Download disponível", cx, y,
                      size=FONT_TINY_SIZE, color=(80, 220, 100), center_x=True)
        else:
            draw_text(self.screen, "🔗 Ver página de download", cx, y,
                      size=FONT_TINY_SIZE, color=(220, 180, 60), center_x=True)

    def _draw_bottom_bar(self) -> None:
        self._btn_back.draw(self.screen)
        self._btn_download.draw(self.screen)
        if self._total_pages > 1:
            self._btn_prev.draw(self.screen)
            self._btn_next.draw(self.screen)
            draw_text(self.screen,
                      f"Pág. {self._page:,} / {self._total_pages:,}",
                      self.w // 2, self.h - self._bottom_bar_h + 26,
                      size=FONT_TINY_SIZE, color=GRAY, center_x=True)

    # ── Layout helpers ─────────────────────────────────────────────────────────

    def _list_top(self) -> int:
        return self._top_bar_h + self._filter_bar_h + self._status_bar_h + 12

    def _list_height(self) -> int:
        return self.h - self._list_top() - self._bottom_bar_h - 8

    def _list_w(self) -> int:
        return self.w - self._detail_w - self._list_x - 12

    def _visible_items(self) -> int:
        return max(1, self._list_height() // self._item_h)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _trim(text: str, max_chars: int) -> str:
    if not text:
        return ""
    return text if len(text) <= max_chars else text[:max_chars - 1] + "…"


def _wrap(text: str, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word[:width]
    if current:
        lines.append(current)
    return lines or [text[:width]]


def _diff_stars(diff: int) -> str:
    """Converte dificuldade 0-6 em estrelas."""
    if diff < 0:
        return ""
    stars = min(diff, 6)
    return "★" * stars + "☆" * (6 - stars)
