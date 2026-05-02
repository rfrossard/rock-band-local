"""
Rock Band Local — Base Screen
Classe base para todas as telas do jogo.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

import pygame

from game.constants import (
    SCREEN_W, SCREEN_H, COLOR_BG, WHITE, GRAY, BLACK,
    FONT_TITLE_SIZE, FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)


class FontCache:
    """Cache global de fontes pygame."""
    _cache: Dict[Tuple[str, int, bool], pygame.font.Font] = {}

    @classmethod
    def get(cls, size: int, bold: bool = False, name: Optional[str] = None) -> pygame.font.Font:
        key = (name or '', size, bold)
        if key not in cls._cache:
            if name:
                try:
                    cls._cache[key] = pygame.font.Font(name, size)
                    return cls._cache[key]
                except Exception:
                    pass
            cls._cache[key] = pygame.font.SysFont('Arial', size, bold=bold)
        return cls._cache[key]


def draw_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    size: int = FONT_MEDIUM_SIZE,
    color: Tuple = WHITE,
    bold: bool = False,
    center_x: bool = False,
    center_y: bool = False,
    alpha: int = 255,
    shadow: bool = False,
) -> pygame.Rect:
    font = FontCache.get(size, bold)
    if shadow:
        shadow_surf = font.render(text, True, BLACK)
        if alpha < 255:
            shadow_surf.set_alpha(alpha // 2)
        sx = x + 1 - (shadow_surf.get_width() // 2 if center_x else 0)
        sy = y + 1 - (shadow_surf.get_height() // 2 if center_y else 0)
        surface.blit(shadow_surf, (sx, sy))

    surf = font.render(text, True, color)
    if alpha < 255:
        surf.set_alpha(alpha)
    rx = x - (surf.get_width() // 2 if center_x else 0)
    ry = y - (surf.get_height() // 2 if center_y else 0)
    surface.blit(surf, (rx, ry))
    return surf.get_rect(topleft=(rx, ry))


def draw_rounded_rect(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: Tuple,
    radius: int = 12,
    alpha: int = 255,
    border_color: Optional[Tuple] = None,
    border_width: int = 2,
) -> None:
    if alpha < 255:
        tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (*color[:3], alpha), tmp.get_rect(), border_radius=radius)
        surface.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


class Button:
    """Botão interativo com hover e animação."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        color: Tuple = GRAY,
        hover_color: Optional[Tuple] = None,
        text_color: Tuple = WHITE,
        font_size: int = FONT_SMALL_SIZE,
        radius: int = 10,
    ):
        self.rect = rect
        self.label = label
        self.color = color
        self.hover_color = hover_color or tuple(min(c + 40, 255) for c in color)
        self.text_color = text_color
        self.font_size = font_size
        self.radius = radius
        self._hovered = False
        self._click_anim = 0.0

    def update(self, mouse_pos: Tuple[int, int]) -> None:
        self._hovered = self.rect.collidepoint(mouse_pos)
        if self._click_anim > 0:
            self._click_anim = max(0.0, self._click_anim - 0.1)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._click_anim = 1.0
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        color = self.hover_color if self._hovered else self.color
        # Click shrink
        r = self.rect.inflate(-int(self._click_anim * 4), -int(self._click_anim * 4))
        draw_rounded_rect(surface, r, color, self.radius)
        draw_text(
            surface, self.label,
            r.centerx, r.centery,
            size=self.font_size,
            color=self.text_color,
            center_x=True, center_y=True,
        )


class BaseScreen:
    """Classe base para todas as telas."""

    def __init__(self, screen: pygame.Surface, config: Dict):
        self.screen = screen
        self.config = config
        self.next_state: Optional[str] = None
        self.next_data: Optional[Any] = None
        self.w = screen.get_width()
        self.h = screen.get_height()
        self._buttons: List[Button] = []

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for btn in self._buttons:
            btn.update(mouse_pos)

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)

    def transition_to(self, state: str, data: Any = None) -> None:
        self.next_state = state
        self.next_data  = data

    def draw_background_grid(self) -> None:
        """Desenha uma grade sutil no fundo."""
        for x in range(0, self.w, 40):
            pygame.draw.line(self.screen, (25, 25, 40), (x, 0), (x, self.h))
        for y in range(0, self.h, 40):
            pygame.draw.line(self.screen, (25, 25, 40), (0, y), (self.w, y))

    def draw_title(self, text: str, y: int = 40, color: Tuple = WHITE) -> None:
        draw_text(
            self.screen, text,
            self.w // 2, y,
            size=FONT_LARGE_SIZE,
            color=color,
            bold=True,
            center_x=True,
            shadow=True,
        )
