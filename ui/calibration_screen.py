"""
Rock Band Local — Calibration Screen
Permite ajustar o offset de latência de áudio/vídeo.
"""
from __future__ import annotations
import time
from typing import Dict

import pygame

from game.audio_engine import AudioEngine
from game.constants import (
    STATE_SETTINGS, STATE_MAIN_MENU,
    COLOR_BG, WHITE, GRAY, COLOR_STAR,
    FRET_COLORS,
    FONT_LARGE_SIZE, FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
)
from ui.base_screen import BaseScreen, Button, draw_text, draw_rounded_rect


BEEP_INTERVAL = 1.0   # segundos entre bipes
FLASH_DURATION = 0.12


class CalibrationScreen(BaseScreen):
    """
    Tela de calibração de latência.

    O usuário ouve um bipe periódico e pressiona qualquer fret/espaço
    quando *vê* o flash visual. A diferença entre o tempo esperado e o
    tempo do aperto é o offset que corrige o jogo.
    """

    def __init__(self, screen: pygame.Surface, config: Dict, audio: AudioEngine):
        super().__init__(screen, config)
        self._audio = audio
        self._offset_ms: float = config.get('audio', {}).get('latency_offset_ms', 0.0)
        self._deltas: list = []
        self._last_beep_time = 0.0
        self._flash_until = 0.0
        self._running_test = False
        self._step = 'intro'   # 'intro' | 'test' | 'result'

        self._btn_start = Button(
            pygame.Rect(self.w // 2 - 120, self.h // 2 + 40, 240, 50),
            "▶  Iniciar Teste",
            color=(30, 100, 30),
        )
        self._btn_save = Button(
            pygame.Rect(self.w // 2 - 100, self.h // 2 + 120, 200, 50),
            "💾  Salvar",
            color=(30, 80, 150),
        )
        self._btn_back = Button(
            pygame.Rect(30, self.h - 70, 140, 44),
            "← Voltar",
            color=(60, 60, 80),
            font_size=FONT_TINY_SIZE,
        )
        self._buttons = [self._btn_start, self._btn_save, self._btn_back]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.transition_to(STATE_MAIN_MENU)

            elif event.key in (pygame.K_SPACE, pygame.K_s, pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k):
                if self._step == 'test':
                    self._register_tap()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._btn_start.is_clicked(event):
                self._start_test()
            elif self._btn_save.is_clicked(event):
                self._save_offset()
                self.transition_to(STATE_MAIN_MENU)
            elif self._btn_back.is_clicked(event):
                self.transition_to(STATE_MAIN_MENU)

    def _start_test(self) -> None:
        self._deltas.clear()
        self._step = 'test'
        self._last_beep_time = time.monotonic() + 1.0
        self._flash_until = 0.0

    def _register_tap(self) -> None:
        now = time.monotonic()
        # Qual era o bipe esperado mais próximo?
        interval = BEEP_INTERVAL
        phase = (now - self._last_beep_time) % interval
        if phase > interval / 2:
            phase -= interval
        self._deltas.append(phase * 1000.0)  # em ms

        # Calcula média após 8+ taps
        if len(self._deltas) >= 8:
            avg = sum(self._deltas[-8:]) / 8.0
            self._offset_ms = -avg
            self._step = 'result'

    def _save_offset(self) -> None:
        self._audio.set_offset(self._offset_ms)
        self.config.setdefault('audio', {})['latency_offset_ms'] = self._offset_ms
        # Persistir no arquivo
        import json, os
        cfg_path = 'config.json'
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            cfg.setdefault('audio', {})['latency_offset_ms'] = self._offset_ms
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

    def update(self, dt: float) -> None:
        super().update(dt)
        if self._step == 'test':
            now = time.monotonic()
            if now >= self._last_beep_time + BEEP_INTERVAL:
                self._last_beep_time += BEEP_INTERVAL
                self._audio.play_beep(880, 80)
                self._flash_until = now + FLASH_DURATION

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        self.draw_background_grid()
        self.draw_title("Calibração de Latência", y=30)

        if self._step == 'intro':
            self._draw_intro()
        elif self._step == 'test':
            self._draw_test()
        elif self._step == 'result':
            self._draw_result()

        self._btn_back.draw(self.screen)

    def _draw_intro(self) -> None:
        lines = [
            "1. Você ouvirá bipes regulares.",
            "2. Pressione ESPAÇO (ou qualquer fret) quando vir o flash visual.",
            "3. Repita 8 vezes — o jogo calculará seu offset automaticamente.",
            "",
            f"Offset atual: {self._offset_ms:+.0f} ms",
        ]
        y = self.h // 2 - 80
        for line in lines:
            color = COLOR_STAR if 'atual' in line else GRAY
            draw_text(self.screen, line, self.w // 2, y,
                      size=FONT_SMALL_SIZE, color=color, center_x=True)
            y += 30

        self._btn_start.draw(self.screen)

    def _draw_test(self) -> None:
        now = time.monotonic()
        flashing = now < self._flash_until

        # Círculo grande que pisca
        radius = 100
        cx, cy = self.w // 2, self.h // 2 - 20
        if flashing:
            color = COLOR_STAR
        else:
            color = (50, 50, 70)

        pygame.draw.circle(self.screen, color, (cx, cy), radius)
        pygame.draw.circle(self.screen, (30, 30, 50), (cx, cy), radius - 10)

        # Progresso
        taps = len(self._deltas)
        draw_text(self.screen, f"Taps: {taps}/8", cx, cy + radius + 30,
                  size=FONT_MEDIUM_SIZE, color=WHITE, center_x=True)

        # Instrução
        draw_text(self.screen, "ESPAÇO ao ver o flash amarelo",
                  cx, cy + radius + 65, size=FONT_SMALL_SIZE, color=GRAY, center_x=True)

        # Últimos deltas
        if self._deltas:
            recent = self._deltas[-1]
            color = (100, 255, 100) if abs(recent) < 30 else (255, 150, 50) if abs(recent) < 60 else (255, 80, 80)
            draw_text(self.screen, f"Último tap: {recent:+.1f} ms",
                      cx, cy + radius + 95, size=FONT_TINY_SIZE, color=color, center_x=True)

    def _draw_result(self) -> None:
        color = (100, 255, 100) if abs(self._offset_ms) < 20 else (255, 180, 50) if abs(self._offset_ms) < 50 else (255, 100, 80)

        draw_text(self.screen, "Offset calculado:", self.w // 2, self.h // 2 - 60,
                  size=FONT_SMALL_SIZE, color=GRAY, center_x=True)
        draw_text(self.screen, f"{self._offset_ms:+.1f} ms", self.w // 2, self.h // 2 - 20,
                  size=FONT_LARGE_SIZE, bold=True, color=color, center_x=True)

        quality = "Excelente!" if abs(self._offset_ms) < 20 else "Bom" if abs(self._offset_ms) < 50 else "Precisa ajuste"
        draw_text(self.screen, quality, self.w // 2, self.h // 2 + 30,
                  size=FONT_SMALL_SIZE, color=color, center_x=True)

        self._btn_save.draw(self.screen)
        self._btn_start.rect.y = self.h // 2 + 180
        self._btn_start.label = "🔁  Refazer Teste"
        self._btn_start.draw(self.screen)
