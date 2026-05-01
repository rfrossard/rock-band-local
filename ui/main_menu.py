"""
Rock Band Local — Main Menu
Visual dark neon estilo YARG.
"""
from __future__ import annotations
import math
import random
import time
from typing import Dict, List

import pygame

from game.constants import (
    STATE_SONG_SELECT, STATE_RHYTHMVERSE, STATE_CALIBRATION, STATE_SETTINGS, STATE_QUIT,
    FRET_COLORS, FRET_GLOW, COLOR_BG, COLOR_PANEL, COLOR_PANEL_LIGHT, COLOR_BORDER,
    WHITE, GRAY,
    COLOR_STAR, COLOR_OVERDRIVE,
    FONT_TITLE_SIZE, FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect, FontCache


MENU_ITEMS = [
    ("🎸  Tocar",                    STATE_SONG_SELECT,  0),
    ("🌐  Rhythmverse",              STATE_RHYTHMVERSE,  1),
    ("🎛️   Calibrar Latência",       STATE_CALIBRATION,  2),
    ("⚙️   Configurações",           STATE_SETTINGS,     3),
    ("🚪  Sair",                     STATE_QUIT,         4),
]


class MainMenu(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict):
        super().__init__(screen, config)
        self._selected = 0
        self._t = time.monotonic()
        self._build_buttons()
        self._particles: List[Dict] = self._make_particles()
        self._scanline_offset = 0.0

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_buttons(self) -> None:
        self._buttons.clear()
        btn_w, btn_h = 440, 58
        n = len(MENU_ITEMS)
        total_h = n * btn_h + (n - 1) * 12
        start_y = self.h // 2 - total_h // 2 + 40

        for i, (label, state, color_idx) in enumerate(MENU_ITEMS):
            x = self.w // 2 - btn_w // 2
            y = start_y + i * (btn_h + 12)
            # Cor da borda: fret color neon
            border_col = FRET_GLOW[color_idx % len(FRET_GLOW)]
            bg_col     = (16, 16, 26)
            hover_col  = (24, 24, 38)

            btn = Button(
                rect=pygame.Rect(x, y, btn_w, btn_h),
                label=label,
                color=bg_col,
                hover_color=hover_col,
                text_color=WHITE,
                font_size=FONT_SMALL_SIZE,
                radius=10,
            )
            # Guardar cor de borda para desenho customizado
            btn._yarg_border = border_col
            btn._yarg_idx    = color_idx
            self._buttons.append(btn)

    def _make_particles(self) -> List[Dict]:
        particles = []
        for _ in range(60):
            particles.append({
                'x':     random.uniform(0, self.w),
                'y':     random.uniform(0, self.h),
                'vx':    random.uniform(-0.2, 0.2),
                'vy':    random.uniform(-0.6, -0.1),
                'size':  random.randint(1, 3),
                'color': FRET_GLOW[random.randint(0, 4)],
                'alpha': random.randint(20, 100),
                'life':  random.uniform(0.0, 1.0),
            })
        return particles

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(MENU_ITEMS)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(MENU_ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self._selected)

        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, btn in enumerate(self._buttons):
                if btn.is_clicked(event):
                    self._activate(i)
                    break

    def _activate(self, idx: int) -> None:
        _, state, _ = MENU_ITEMS[idx]
        self.transition_to(state)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        super().update(dt)
        self._scanline_offset = (self._scanline_offset + dt * 40) % self.h

        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] += dt * 0.3
            if p['life'] >= 1.0 or p['y'] < -10:
                # Reset
                p['y']    = self.h + 10
                p['x']    = random.uniform(0, self.w)
                p['vx']   = random.uniform(-0.2, 0.2)
                p['vy']   = random.uniform(-0.6, -0.1)
                p['life'] = 0.0
                p['color']= FRET_GLOW[random.randint(0, 4)]

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self._draw_grid()
        self._draw_particles()
        self._draw_scanlines()
        self._draw_logo()
        self._draw_buttons()
        self._draw_hint()

    def _draw_grid(self) -> None:
        """Grade de fundo tênue estilo YARG."""
        t = time.monotonic() - self._t
        grid_col = (18, 18, 30)
        spacing = 60
        # Linhas verticais
        for xi in range(0, self.w + spacing, spacing):
            pygame.draw.line(self.screen, grid_col, (xi, 0), (xi, self.h))
        # Linhas horizontais animadas (movem suavemente para cima)
        scroll = (t * 20) % spacing
        for yi in range(-spacing, self.h + spacing, spacing):
            y = int(yi + scroll)
            pygame.draw.line(self.screen, grid_col, (0, y), (self.w, y))

    def _draw_scanlines(self) -> None:
        """Scanlines CRT sutis — assinatura estética retro YARG."""
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y in range(0, self.h, 4):
            s.fill((0, 0, 0, 18), (0, y, self.w, 2))
        self.screen.blit(s, (0, 0))

    def _draw_particles(self) -> None:
        for p in self._particles:
            a = int(p['alpha'] * (1.0 - p['life']))
            if a <= 0:
                continue
            s = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p['color'], a), (p['size'], p['size']), p['size'])
            self.screen.blit(s, (int(p['x']) - p['size'], int(p['y']) - p['size']))

    def _draw_logo(self) -> None:
        t = time.monotonic() - self._t

        # ── Logo principal ────────────────────────────────────────────────────
        # Halo animado atrás do logo
        pulse = 0.5 + 0.5 * math.sin(t * 1.5)
        halo_r = int(200 + 20 * pulse)
        halo_surf = pygame.Surface((halo_r * 2, halo_r // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(halo_surf, (40, 60, 140, int(30 * pulse)),
                            (0, 0, halo_r * 2, halo_r // 2))
        self.screen.blit(halo_surf, (self.w // 2 - halo_r, 30))

        # Título com letras coloridas por fret
        title = "ROCK BAND LOCAL"
        font_size = int(FONT_LARGE_SIZE * (1.0 + 0.025 * math.sin(t * 2.0)))
        font = pygame.font.SysFont('Arial', font_size, bold=True)

        # Medir largura total
        total_w = font.size(title)[0]
        x_start = self.w // 2 - total_w // 2
        y_title = 55

        # Renderizar letra por letra com cores neon alternadas
        x_cur = x_start
        for ci, ch in enumerate(title):
            col = FRET_GLOW[ci % len(FRET_GLOW)] if ch != ' ' else WHITE
            glyph = font.render(ch, True, col)
            # Sombra
            shadow = font.render(ch, True, (0, 0, 0))
            self.screen.blit(shadow, (x_cur + 2, y_title + 2))
            self.screen.blit(glyph, (x_cur, y_title))
            x_cur += glyph.get_width()

        # Ícone de nota musical pulsante à esquerda do título
        note_x = x_start - 48
        note_pulse = 1.0 + 0.15 * math.sin(t * 3.0)
        nf = pygame.font.SysFont('Arial', int(40 * note_pulse), bold=True)
        note_surf = nf.render("♪", True, COLOR_STAR)
        self.screen.blit(note_surf, (note_x, y_title + 4))

        # Linha separadora neon
        bar_y = y_title + font_size + 8
        bar_w = 520
        for bx in range(bar_w):
            frac = bx / bar_w
            col_idx = int(frac * len(FRET_GLOW))
            col = FRET_GLOW[col_idx % len(FRET_GLOW)]
            alpha = int(200 * math.sin(math.pi * frac))
            s = pygame.Surface((1, 2), pygame.SRCALPHA)
            s.fill((*col, alpha))
            self.screen.blit(s, (self.w // 2 - bar_w // 2 + bx, bar_y))

        # Subtítulo
        sub = "YARG  ·  Clone Hero  ·  Frets on Fire  ·  World Tour"
        draw_text(self.screen, sub, self.w // 2, bar_y + 14,
                  size=FONT_TINY_SIZE, color=(70, 70, 100), center_x=True)

    def _draw_buttons(self) -> None:
        t = time.monotonic() - self._t
        for i, btn in enumerate(self._buttons):
            is_sel = (i == self._selected)
            border = getattr(btn, '_yarg_border', WHITE)
            col_idx = getattr(btn, '_yarg_idx', i)

            # Sombra do botão
            shadow_rect = btn.rect.move(3, 3)
            shadow_surf = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 80))
            self.screen.blit(shadow_surf, shadow_rect.topleft)

            # Fundo do botão
            bg = (22, 22, 36) if not is_sel else (28, 28, 46)
            draw_rounded_rect(self.screen, btn.rect, bg, radius=10)

            # Borda neon
            if is_sel:
                # Borda pulsante e mais brilhante quando selecionado
                pulse_a = int(180 + 75 * math.sin(t * 4))
                bw = 2
                bs = pygame.Surface((btn.rect.width + 4, btn.rect.height + 4), pygame.SRCALPHA)
                pygame.draw.rect(bs, (*border, pulse_a),
                                 (0, 0, btn.rect.width + 4, btn.rect.height + 4),
                                 bw, border_radius=12)
                self.screen.blit(bs, (btn.rect.x - 2, btn.rect.y - 2))

                # Glow de fundo sutil
                glow_surf = pygame.Surface((btn.rect.width + 20, btn.rect.height + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*border, 18),
                                 (0, 0, btn.rect.width + 20, btn.rect.height + 20),
                                 border_radius=14)
                self.screen.blit(glow_surf, (btn.rect.x - 10, btn.rect.y - 10))
            else:
                # Borda sutil fina
                bs = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
                pygame.draw.rect(bs, (*border, 60),
                                 (0, 0, btn.rect.width, btn.rect.height),
                                 1, border_radius=10)
                self.screen.blit(bs, btn.rect.topleft)

            # Barra colorida lateral esquerda (estilo YARG)
            bar_color = border if is_sel else tuple(c // 3 for c in border)
            bar_h = btn.rect.height - 16
            bar_rect = pygame.Rect(btn.rect.x + 6, btn.rect.y + 8, 4, bar_h)
            pygame.draw.rect(self.screen, bar_color, bar_rect, border_radius=2)

            # Texto do botão
            text_col = WHITE if is_sel else (170, 170, 200)
            font = FontCache.get(btn.font_size, bold=True)
            text_surf = font.render(btn.label, True, text_col)
            tx = btn.rect.x + 20
            ty = btn.rect.centery - text_surf.get_height() // 2
            self.screen.blit(text_surf, (tx, ty))

            # Ícone de seta direita quando selecionado
            if is_sel:
                arrow_x = btn.rect.right - 20
                arrow_y = btn.rect.centery
                af = FontCache.get(18, bold=True)
                as_ = af.render("▶", True, border)
                self.screen.blit(as_, (arrow_x - as_.get_width() // 2, arrow_y - as_.get_height() // 2))

    def _draw_hint(self) -> None:
        draw_text(
            self.screen,
            "↑↓  navegar     ENTER  selecionar     F11  tela cheia",
            self.w // 2, self.h - 22,
            size=FONT_TINY_SIZE, color=(45, 45, 70), center_x=True,
        )
