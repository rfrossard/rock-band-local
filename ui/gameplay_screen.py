"""
Rock Band Local — Gameplay Screen
Highway de notas em perspectiva 3D estilo YARG.
Dark theme com gems neon, HUD com crowd meter, bubble multiplicador e SP bar.
"""
from __future__ import annotations
import math
import time
from typing import Dict, List, Optional, Set, Tuple

import pygame

from game.audio_engine import AudioEngine
from game.chart_parser import Chart, Note, ticks_to_ms as chart_ticks_to_ms
from game.input_handler import InputManager, FretEvent, StrumEvent, PadEvent, StarPowerEvent
from game.note_engine import GameSession
from game.scoring import ScoreState
from game.constants import (
    STATE_RESULTS, STATE_SONG_SELECT,
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
    FRET_COLORS, FRET_GLOW, FRET_INNER, PAD_COLORS,
    COLOR_BG, COLOR_HIGHWAY, COLOR_HIGHWAY_SP, COLOR_LINE, COLOR_LINE_BEAT,
    COLOR_LINE_MEASURE, COLOR_STAR, COLOR_STAR_DIM, COLOR_OVERDRIVE,
    COLOR_SP_BAR, COLOR_SP_ACTIVE, COLOR_MULT_BG, COLOR_MULT_SP,
    COLOR_CROWD_OK, COLOR_CROWD_BAD,
    COLOR_HIT_PERFECT, COLOR_HIT_GREAT, COLOR_HIT_GOOD, COLOR_HIT_OK, COLOR_HIT_MISS,
    WHITE, GRAY, DGRAY, BLACK,
    HWY_BOTTOM_W, HWY_TOP_W, HWY_TOP_Y_RATIO, HWY_HIT_Y_RATIO, HIT_TARGET_RADIUS,
    NOTE_RADIUS, HIT_LINE_Y_RATIO,
    FONT_MEDIUM_SIZE, FONT_SMALL_SIZE, FONT_TINY_SIZE,
    SCREEN_W, SCREEN_H,
)
from ui.base_screen import BaseScreen, draw_text, draw_rounded_rect, FontCache


# ── Constantes de feedback ────────────────────────────────────────────────────
HIGHWAY_LANES = {
    INSTRUMENT_GUITAR: 5,
    INSTRUMENT_BASS:   5,
    INSTRUMENT_DRUMS:  5,
    INSTRUMENT_VOCALS: 1,
}

HIT_FEEDBACK_COLORS = {
    'perfect': COLOR_HIT_PERFECT,
    'great':   COLOR_HIT_GREAT,
    'good':    COLOR_HIT_GOOD,
    'ok':      COLOR_HIT_OK,
    'miss':    COLOR_HIT_MISS,
}
HIT_FEEDBACK_LABELS = {
    'perfect': 'PERFECT!',
    'great':   'GREAT!',
    'good':    'GOOD',
    'ok':      'OKAY',
    'miss':    'MISS',
}
HIT_FEEDBACK_SIZE = {
    'perfect': 30,
    'great':   28,
    'good':    24,
    'ok':      20,
    'miss':    22,
}


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ── Highway 3D perspective renderer ──────────────────────────────────────────

class Highway3D:
    """
    Renderiza o highway de notas em perspectiva 3D estilo YARG.
    Trapézio: largo na linha de hit (bottom), estreito no topo (far).
    """

    def __init__(self, center_x: int, screen_h: int, instrument: str, config: Dict, player_idx: int = 0):
        self.center_x  = center_x
        self.screen_h  = screen_h
        self.instrument = instrument
        self.config    = config
        self.player_idx = player_idx
        self.n_lanes   = HIGHWAY_LANES.get(instrument, 5)

        # Dimensões verticais
        self.top_y    = int(screen_h * HWY_TOP_Y_RATIO)
        self.hit_y    = int(screen_h * HWY_HIT_Y_RATIO)

        # Larguras (half widths)
        self.bottom_hw = HWY_BOTTOM_W // 2   # half-width na hit line
        self.top_hw    = HWY_TOP_W // 2      # half-width no topo

        # Hit flash per lane
        self._hit_flash: Dict[int, float] = {}
        self._sp_active = False

    # ── Projeção perspectiva ───────────────────────────────────────────────────

    def project(self, lane_frac: float, depth: float) -> Tuple[int, int]:
        """
        Projeta um ponto no highway.
        lane_frac: 0.0 = extremo esquerdo, 1.0 = extremo direito
        depth: 0.0 = hit line (bottom), 1.0 = topo (far)
        Retorna (x, y) em pixels.
        """
        hw = lerp(self.bottom_hw, self.top_hw, depth)
        left_x = self.center_x - hw
        x = int(left_x + lane_frac * 2 * hw)
        y = int(lerp(self.hit_y, self.top_y, depth))
        return x, y

    def lane_x(self, lane: int, depth: float) -> int:
        """Centro X de uma lane em determinada profundidade."""
        frac = (lane + 0.5) / self.n_lanes
        x, _ = self.project(frac, depth)
        return x

    def lane_width_at(self, depth: float) -> float:
        """Largura de uma lane na profundidade dada."""
        hw = lerp(self.bottom_hw, self.top_hw, depth)
        return (2 * hw) / self.n_lanes

    def note_depth(self, note_time_ms: float, pos_ms: float, window_ms: float) -> float:
        """Converte tempo da nota em depth (0=hit, 1=topo/far). Negativo = passou."""
        return (note_time_ms - pos_ms) / window_ms

    # ── Background da highway ─────────────────────────────────────────────────

    def draw_background(self, surface: pygame.Surface, held_frets: Set[int],
                        beat_times: List[float], pos_ms: float, window_ms: float,
                        sp_active: bool = False) -> None:
        self._sp_active = sp_active

        # Trapézio de fundo
        self._draw_highway_trap(surface, sp_active)
        # Linhas de beat se movendo
        self._draw_beat_lines(surface, beat_times, pos_ms, window_ms)
        # Linhas divisórias verticais de lanes
        self._draw_lane_dividers(surface)
        # Glow das lanes seguradas
        self._draw_held_glow(surface, held_frets)
        # Hit targets na linha de hit
        self._draw_hit_targets(surface, held_frets)
        # Hit flash
        self._draw_hit_flash(surface)

    def _draw_highway_trap(self, surface: pygame.Surface, sp_active: bool) -> None:
        """Desenha o trapézio de fundo do highway."""
        # Pontos do trapézio
        tl = (self.center_x - self.top_hw,    self.top_y)
        tr = (self.center_x + self.top_hw,    self.top_y)
        br = (self.center_x + self.bottom_hw, self.hit_y)
        bl = (self.center_x - self.bottom_hw, self.hit_y)

        hwy_color = COLOR_HIGHWAY_SP if sp_active else COLOR_HIGHWAY
        pygame.draw.polygon(surface, hwy_color, [tl, tr, br, bl])

        # Borda do trapézio
        border_color = (60, 120, 200) if sp_active else (40, 40, 65)
        pygame.draw.polygon(surface, border_color, [tl, tr, br, bl], 2)

        # Gradiente de fade no topo (vanish)
        fade_h = int((self.hit_y - self.top_y) * 0.25)
        for i in range(fade_h):
            t = i / fade_h
            alpha = int(200 * (1.0 - t))
            hw_at = lerp(self.top_hw, self.top_hw + (self.bottom_hw - self.top_hw) * (i / (self.hit_y - self.top_y)), 1.0)
            # Linha horizontal de fade
            left_x = self.center_x - int(lerp(self.top_hw, self.bottom_hw, i / (self.hit_y - self.top_y)))
            right_x = self.center_x + int(lerp(self.top_hw, self.bottom_hw, i / (self.hit_y - self.top_y)))
            y = self.top_y + i
            fade_surf = pygame.Surface((right_x - left_x, 1), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, alpha))
            surface.blit(fade_surf, (left_x, y))

    def _draw_beat_lines(self, surface: pygame.Surface, beat_times: List[float],
                         pos_ms: float, window_ms: float) -> None:
        """Desenha linhas de beat que se movem junto com a música."""
        for bt in beat_times:
            depth = self.note_depth(bt, pos_ms, window_ms)
            if depth < 0.0 or depth > 1.0:
                continue
            left_x, y = self.project(0.0, depth)
            right_x, _ = self.project(1.0, depth)
            # Linhas de medida mais brilhantes
            col = COLOR_LINE_MEASURE if bt % 1000 < 10 else COLOR_LINE_BEAT
            pygame.draw.line(surface, col, (left_x, y), (right_x, y), 1)

    def _draw_lane_dividers(self, surface: pygame.Surface) -> None:
        """Desenha linhas verticais dividindo as lanes em perspectiva."""
        for i in range(1, self.n_lanes):
            frac = i / self.n_lanes
            x_top, y_top = self.project(frac, 1.0)
            x_bot, y_bot = self.project(frac, 0.0)
            pygame.draw.line(surface, (35, 35, 58), (x_top, y_top), (x_bot, y_bot), 1)

    def _draw_held_glow(self, surface: pygame.Surface, held_frets: Set[int]) -> None:
        """Lane glow para frets segurados."""
        for lane in range(self.n_lanes):
            if lane not in held_frets:
                continue
            glow_color = FRET_GLOW[lane % len(FRET_GLOW)]
            # Triângulo de glow para a lane
            frac_l = lane / self.n_lanes
            frac_r = (lane + 1) / self.n_lanes
            pts = [
                self.project(frac_l, 1.0),
                self.project(frac_r, 1.0),
                self.project(frac_r, 0.0),
                self.project(frac_l, 0.0),
            ]
            glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (*glow_color, 25), pts)
            surface.blit(glow_surf, (0, 0))

    def _draw_hit_targets(self, surface: pygame.Surface, held_frets: Set[int]) -> None:
        """Desenha os botões circulares coloridos na linha de hit (YARG style)."""
        r = HIT_TARGET_RADIUS
        for lane in range(self.n_lanes):
            cx = self.lane_x(lane, 0.0)
            cy = self.hit_y
            color = FRET_COLORS[lane % len(FRET_COLORS)]
            glow  = FRET_GLOW[lane % len(FRET_GLOW)]
            inner = FRET_INNER[lane % len(FRET_INNER)]
            is_held = lane in held_frets

            # Glow externo quando segurado
            if is_held:
                for ring in range(4, 0, -1):
                    a = int(80 * ring / 4)
                    gs = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*glow, a), (r + 8, r + 8), r + ring * 3)
                    surface.blit(gs, (cx - r - 8, cy - r - 8))

            # Círculo principal
            pygame.draw.circle(surface, color, (cx, cy), r)
            # Aro escuro interno
            dark = tuple(max(0, c - 80) for c in color)
            pygame.draw.circle(surface, dark, (cx, cy), r - 5)
            # Reflexo/brilho interno (quando segurado = mais brilhante)
            refl = inner if is_held else tuple(max(0, c - 40) for c in color)
            pygame.draw.circle(surface, refl, (cx - r // 5, cy - r // 5), r // 4)
            # Borda
            border = glow if is_held else color
            pygame.draw.circle(surface, border, (cx, cy), r, 2)

        # Linha de hit branca
        lx, _ = self.project(0.0, 0.0)
        rx, _ = self.project(1.0, 0.0)
        pygame.draw.line(surface, (200, 200, 220), (lx, self.hit_y), (rx, self.hit_y), 2)

    def _draw_hit_flash(self, surface: pygame.Surface) -> None:
        """Flash colorido na hit line ao acertar."""
        now = time.monotonic()
        for lane, expiry in list(self._hit_flash.items()):
            if now >= expiry:
                del self._hit_flash[lane]
                continue
            age = 0.25 - (expiry - now)
            t = age / 0.25
            alpha = int(220 * (1.0 - t))
            glow = FRET_GLOW[lane % len(FRET_GLOW)]
            cx = self.lane_x(lane, 0.0)
            r = int(lerp(HIT_TARGET_RADIUS + 10, HIT_TARGET_RADIUS + 35, t))
            fs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fs, (*glow, alpha), (r, r), r)
            surface.blit(fs, (cx - r, self.hit_y - r))

    # ── Notas ────────────────────────────────────────────────────────────────

    def draw_notes(self, surface: pygame.Surface, notes: List[Note],
                   pos_ms: float, window_ms: float) -> None:
        """Desenha as notas em perspectiva com gems neon e halos."""
        # Ordenar por depth para desenhar de longe para perto (painter's algo)
        visible = []
        for note in notes:
            if note.hit:
                continue
            depth = self.note_depth(note.time_ms, pos_ms, window_ms)
            if depth < -0.05 or depth > 1.02:
                continue
            visible.append((depth, note))
        visible.sort(key=lambda x: -x[0])  # far first

        for depth, note in visible:
            lane = note.fret % self.n_lanes
            cx, cy = self.project((lane + 0.5) / self.n_lanes, depth)
            lw = self.lane_width_at(depth)

            color = FRET_COLORS[lane % len(FRET_COLORS)]
            glow  = FRET_GLOW[lane % len(FRET_GLOW)]
            inner = FRET_INNER[lane % len(FRET_INNER)]
            if note.is_star_power:
                color = COLOR_OVERDRIVE
                glow  = COLOR_SP_ACTIVE
                inner = (220, 240, 255)

            # Raio da gem escala com perspectiva
            base_r = max(6, int(NOTE_RADIUS * (lw / (HWY_BOTTOM_W / self.n_lanes))))

            # Sustain tail
            if note.sustain_ms > 50:
                end_depth = self.note_depth(note.end_time_ms, pos_ms, window_ms)
                end_depth = clamp(end_depth, -0.02, 1.02)
                ecx, ecy = self.project((lane + 0.5) / self.n_lanes, end_depth)
                tail_w = max(4, int(lw * 0.18))
                pts_l = [
                    self.project(lane / self.n_lanes + 0.5/self.n_lanes - tail_w/2 / (2*self.bottom_hw), depth),
                    self.project(lane / self.n_lanes + 0.5/self.n_lanes - tail_w/2 / (2*self.bottom_hw), end_depth),
                    self.project(lane / self.n_lanes + 0.5/self.n_lanes + tail_w/2 / (2*self.bottom_hw), end_depth),
                    self.project(lane / self.n_lanes + 0.5/self.n_lanes + tail_w/2 / (2*self.bottom_hw), depth),
                ]
                tail_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                tail_alpha = 160 if not note.is_star_power else 200
                pygame.draw.polygon(tail_surf, (*color[:3], tail_alpha), pts_l)
                surface.blit(tail_surf, (0, 0))

            self._draw_gem(surface, cx, cy, base_r, color, glow, inner,
                           is_hopo=getattr(note, 'is_hopo', False),
                           is_sp=note.is_star_power,
                           depth=depth)

    def _draw_gem(self, surface: pygame.Surface, cx: int, cy: int, r: int,
                  color: tuple, glow: tuple, inner: tuple,
                  is_hopo: bool = False, is_sp: bool = False, depth: float = 0.5) -> None:
        """Desenha uma gem neon com halo (estilo YARG)."""
        if r < 3:
            return

        # Halo externo (glow) — camadas de alpha decrescente
        for ring in (3, 2, 1):
            a = int(60 * ring / 3)
            gs = pygame.Surface((r * 2 + ring * 8, r * 2 + ring * 8), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow, a), (r + ring * 4, r + ring * 4), r + ring * 3)
            surface.blit(gs, (cx - r - ring * 4, cy - r - ring * 4))

        # Círculo base
        pygame.draw.circle(surface, color, (cx, cy), r)

        # Aro escuro interno
        dark = tuple(max(0, c - 100) for c in color)
        if r > 8:
            pygame.draw.circle(surface, dark, (cx, cy), max(2, r - 5))

        # Reflexo/brilho interno (pequeno highlight)
        if r > 10:
            pygame.draw.circle(surface, inner, (cx - r // 4, cy - r // 4), r // 4)

        # Borda brilhante
        pygame.draw.circle(surface, glow, (cx, cy), r, 2)

        # Indicador HOPO (triângulo ou ponto no centro)
        if is_hopo and r > 8:
            pygame.draw.circle(surface, WHITE, (cx, cy), r // 3)

    def flash_hit(self, lane: int) -> None:
        self._hit_flash[lane] = time.monotonic() + 0.25

    @property
    def rect(self) -> pygame.Rect:
        """Bounding box aproximado do highway (compat. com código legado)."""
        left  = self.center_x - self.bottom_hw
        return pygame.Rect(left, self.top_y, self.bottom_hw * 2, self.hit_y - self.top_y)


# ── Gameplay Screen ──────────────────────────────────────────────────────────

class GameplayScreen(BaseScreen):

    def __init__(self, screen: pygame.Surface, config: Dict, data: Dict,
                 input_mgr: InputManager, audio_engine: AudioEngine):
        super().__init__(screen, config)
        self._data = data
        self._input_mgr = input_mgr
        self._audio = audio_engine

        self._chart: Chart = data['chart']
        self._folder: str  = data['folder']
        self._player_cfgs: List[Dict] = data['players']
        self._n_players = len(self._player_cfgs)

        self._session: Optional[GameSession] = None
        self._highways: List[Highway3D] = []
        self._state = 'countdown'
        self._countdown = 3.0
        self._pos_ms: float = 0.0
        self._window_ms: float = config.get('video', {}).get('note_highway_length_ms', 2000)
        self._start_time: float = 0.0
        self._song_started = False
        self._feedback_labels: List[Dict] = []

        # Crowd meter (performance) — começa em 50%
        self._crowd: List[float] = [0.5] * self._n_players

        # Beat times cache for drawing grid lines
        self._beat_times: List[float] = []

        self._setup()

    def _setup(self) -> None:
        self._session = GameSession(self._chart, self._player_cfgs, self.config)

        for i, p_input in enumerate(self._input_mgr.players):
            if i >= len(self._session.sessions):
                break

            def make_strum_cb(pi):
                def cb(ev: StrumEvent):
                    self._session.on_strum(pi, self._pos_ms)
                    inst = self._player_cfgs[pi].get('instrument')
                    if inst in (INSTRUMENT_GUITAR, INSTRUMENT_BASS):
                        held = self._input_mgr.players[pi].held_frets
                        for lane in held:
                            if pi < len(self._highways):
                                self._highways[pi].flash_hit(lane)
                    self._spawn_feedback(pi)
                    self._update_crowd(pi)
                return cb

            def make_fret_cb(pi):
                def cb(ev: FretEvent):
                    self._session.on_frets_changed(pi, self._input_mgr.players[pi].held_frets)
                return cb

            def make_pad_cb(pi):
                def cb(ev: PadEvent):
                    self._session.on_pad(pi, ev.pad, self._pos_ms)
                    if pi < len(self._highways):
                        self._highways[pi].flash_hit(ev.pad)
                    self._spawn_feedback(pi)
                    self._update_crowd(pi)
                return cb

            def make_sp_cb(pi):
                def cb(ev: StarPowerEvent):
                    self._session.on_star_power(pi)
                return cb

            p_input.on_strum      = make_strum_cb(i)
            p_input.on_fret       = make_fret_cb(i)
            p_input.on_pad        = make_pad_cb(i)
            p_input.on_star_power = make_sp_cb(i)

        self._build_highways()
        self._build_beat_times()
        self._audio.load_song(self._folder, self._chart.metadata.audio_streams)

    def _build_beat_times(self) -> None:
        """Gera lista de beat times para as linhas de grade do highway."""
        dur = max(self._chart.duration_ms, 30_000)
        bpm_events = self._chart.bpm_events
        resolution = self._chart.resolution

        if not bpm_events:
            bpm = 120.0
            interval = 60000.0 / bpm
            t = 0.0
            while t < dur:
                self._beat_times.append(t)
                t += interval
            return

        for j, ev in enumerate(bpm_events):
            t_ms = chart_ticks_to_ms(ev.tick, bpm_events, resolution)
            if j + 1 < len(bpm_events):
                next_t = chart_ticks_to_ms(bpm_events[j + 1].tick, bpm_events, resolution)
            else:
                next_t = dur
            interval = 60000.0 / ev.bpm
            t = t_ms
            while t < next_t:
                self._beat_times.append(t)
                t += interval

    def _update_crowd(self, pi: int) -> None:
        if pi >= len(self._session.sessions):
            return
        fb = self._session.sessions[pi].last_hit_feedback
        if fb in ('perfect', 'great', 'good'):
            self._crowd[pi] = min(1.0, self._crowd[pi] + 0.03)
        elif fb == 'ok':
            pass  # neutro
        elif fb == 'miss':
            self._crowd[pi] = max(0.0, self._crowd[pi] - 0.05)

    def _build_highways(self) -> None:
        self._highways.clear()
        n = self._n_players
        # Distribuir highways horizontalmente
        spacing = 40
        total_w = n * HWY_BOTTOM_W + (n - 1) * spacing
        start_cx = self.w // 2 - total_w // 2 + HWY_BOTTOM_W // 2

        for i, pcfg in enumerate(self._player_cfgs):
            cx = start_cx + i * (HWY_BOTTOM_W + spacing)
            inst = pcfg.get('instrument', INSTRUMENT_GUITAR)
            self._highways.append(Highway3D(cx, self.h, inst, self.config, i))

    def _spawn_feedback(self, player_idx: int) -> None:
        if player_idx >= len(self._session.sessions):
            return
        s = self._session.sessions[player_idx]
        fb = s.last_hit_feedback
        if not fb:
            return
        color = HIT_FEEDBACK_COLORS.get(fb, WHITE)
        label = HIT_FEEDBACK_LABELS.get(fb, '')
        size  = HIT_FEEDBACK_SIZE.get(fb, 24)
        if player_idx < len(self._highways):
            hwy = self._highways[player_idx]
            x = hwy.center_x
            y = hwy.hit_y - 60
        else:
            x, y = self.w // 2, self.h // 2
        self._feedback_labels.append({
            'text': label, 'color': color, 'size': size,
            'x': x, 'y': y, 'alpha': 255,
            'ts': time.monotonic(),
        })

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._state == 'playing':
                    self._pause()
                elif self._state == 'paused':
                    self.transition_to(STATE_SONG_SELECT)
            elif event.key == pygame.K_p:
                if self._state == 'playing':
                    self._pause()
                elif self._state == 'paused':
                    self._resume()
        self._input_mgr.process_events([event])

    def _pause(self) -> None:
        self._state = 'paused'
        self._audio.pause()

    def _resume(self) -> None:
        self._state = 'playing'
        self._audio.resume()

    def update(self, dt: float) -> None:
        super().update(dt)

        if self._state == 'countdown':
            self._countdown -= dt
            if self._countdown <= 0:
                self._state = 'playing'
                self._start_time = time.monotonic()
                self._audio.play()

        elif self._state == 'playing':
            self._pos_ms = self._audio.position_ms

            vocal_sample = self._input_mgr.get_vocal_pitch()
            for i, pcfg in enumerate(self._player_cfgs):
                if pcfg.get('instrument') == INSTRUMENT_VOCALS and vocal_sample:
                    self._session.on_vocal_pitch(
                        i, vocal_sample.pitch_hz, vocal_sample.confidence, self._pos_ms
                    )

            self._session.update(self._pos_ms)
            self._session.update_star_power(dt)

            dur = self._chart.duration_ms
            if dur > 0 and self._pos_ms > dur + 3000:
                self._finish()

            for fb in self._feedback_labels[:]:
                age = time.monotonic() - fb['ts']
                fb['alpha'] = max(0, int(255 * (1.0 - age / 0.9)))
                fb['y'] -= 1.5
                if fb['alpha'] == 0:
                    self._feedback_labels.remove(fb)

    def _finish(self) -> None:
        self._audio.fade_out(2000)
        self._state = 'finished'
        results = []
        for s in self._session.sessions:
            results.append({
                'score':      s.scorer.state.score,
                'accuracy':   s.scorer.state.accuracy_pct,
                'stars':      s.scorer.state.stars,
                'grade':      s.scorer.get_grade_letter(),
                'max_streak': s.scorer.state.max_streak,
                'notes_hit':  s.scorer.state.notes_hit,
                'notes_total':s.scorer.state.notes_total,
                'full_combo': s.scorer.state.full_combo,
                'instrument': self._player_cfgs[s.player_idx].get('instrument', '?'),
                'difficulty': self._player_cfgs[s.player_idx].get('difficulty', '?'),
            })
        self.transition_to(STATE_RESULTS, {
            'chart':   self._chart,
            'results': results,
        })

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)

        if self._state == 'countdown':
            self._draw_highways_bg()
            self._draw_countdown()
            return

        # Background com vinheta
        self._draw_vignette()

        # Highways (background + notas)
        self._draw_highways_bg()
        self._draw_highways_notes()

        # HUD superior (crowd meter + song progress)
        self._draw_top_hud()

        # HUD por highway (score, multiplicador, SP bar)
        self._draw_player_huds()

        # Feedback labels
        for fb in self._feedback_labels:
            draw_text(self.screen, fb['text'], int(fb['x']), int(fb['y']),
                      size=fb['size'], color=fb['color'], bold=True,
                      center_x=True, alpha=fb['alpha'])

        if self._state == 'paused':
            self._draw_pause_overlay()

    def _draw_vignette(self) -> None:
        """Vinheta escura nas bordas (característica visual YARG)."""
        v = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for i in range(80):
            t = i / 80
            a = int(120 * (1.0 - t))
            pygame.draw.rect(v, (0, 0, 0, a), (i, i, self.w - 2*i, self.h - 2*i), 1)
        self.screen.blit(v, (0, 0))

    def _draw_highways_bg(self) -> None:
        held_sets = [
            self._input_mgr.players[i].held_frets if i < len(self._input_mgr.players) else set()
            for i in range(self._n_players)
        ]
        for i, hwy in enumerate(self._highways):
            sp = (i < len(self._session.sessions) and
                  self._session.sessions[i].scorer.state.star_power_active) if self._session else False
            hwy.draw_background(
                self.screen, held_sets[i],
                self._beat_times, self._pos_ms, self._window_ms,
                sp_active=sp,
            )

    def _draw_highways_notes(self) -> None:
        if not self._session:
            return
        for i, hwy in enumerate(self._highways):
            notes = self._session.get_visible_notes(i, self._pos_ms, self._window_ms)
            hwy.draw_notes(self.screen, notes, self._pos_ms, self._window_ms)

    def _draw_top_hud(self) -> None:
        """HUD superior: crowd meter e barra de progresso."""
        # Song title (pequeno, centro topo)
        title = getattr(self._chart.metadata, 'display_name', '') if self._chart.metadata else ''
        if title:
            draw_text(self.screen, title, self.w // 2, 12,
                      size=FONT_TINY_SIZE, color=(100, 100, 130), center_x=True)

        # Progress bar (muito fina, abaixo do título)
        dur = self._chart.duration_ms
        if dur > 0 and self._pos_ms > 0:
            ratio = min(1.0, self._pos_ms / dur)
            bar_w = self.w - 40
            bar_x = 20
            bar_y = 28
            pygame.draw.rect(self.screen, (20, 20, 32), (bar_x, bar_y, bar_w, 4), border_radius=2)
            pygame.draw.rect(self.screen, (60, 100, 200),
                             (bar_x, bar_y, int(bar_w * ratio), 4), border_radius=2)

        # Crowd meter (para cada jogador, ou combinado)
        if self._n_players == 1:
            self._draw_crowd_meter_single(self._crowd[0])
        else:
            # Multi: uma barrinha por jogador abaixo do highway correspondente
            pass  # feito no player HUD

    def _draw_crowd_meter_single(self, crowd: float) -> None:
        """Crowd/Performance meter: barra horizontal central estilo YARG."""
        bar_w = 300
        bar_h = 10
        bar_x = self.w // 2 - bar_w // 2
        bar_y = 38

        # Fundo
        pygame.draw.rect(self.screen, (20, 20, 35), (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        # Fill — cor muda com crowd level
        if crowd >= 0.6:
            fill_col = lerp_color(COLOR_CROWD_OK, (100, 255, 150), (crowd - 0.6) / 0.4)
        elif crowd <= 0.3:
            fill_col = lerp_color(COLOR_CROWD_BAD, (255, 150, 50), (0.3 - crowd) / 0.3)
        else:
            fill_col = lerp_color(COLOR_CROWD_BAD, COLOR_CROWD_OK, (crowd - 0.3) / 0.3)

        fill_w = int(bar_w * crowd)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fill_col,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=5)

        # Marcador de 50% (linha central)
        mid_x = bar_x + bar_w // 2
        pygame.draw.rect(self.screen, WHITE, (mid_x - 1, bar_y - 2, 2, bar_h + 4))

        # Ícone de crowd (texto pequeno)
        draw_text(self.screen, "♫ CROWD", self.w // 2, bar_y + bar_h + 6,
                  size=12, color=(60, 60, 90), center_x=True)

    def _draw_player_huds(self) -> None:
        """HUD por jogador: score, multiplicador (bubble), SP bar, accuracy."""
        for i, sess in enumerate(self._session.sessions if self._session else []):
            state: ScoreState = sess.scorer.state
            hwy = self._highways[i] if i < len(self._highways) else None
            if not hwy:
                continue

            hit_y = hwy.hit_y
            rect  = hwy.rect

            # ── Score (acima do highway) ─────────────────────────────────
            score_y = max(60, hwy.top_y - 36)
            draw_text(self.screen, f"{state.score:,}",
                      hwy.center_x, score_y,
                      size=FONT_MEDIUM_SIZE, bold=True, color=WHITE, center_x=True)

            # ── Multiplicador bubble (canto inferior esquerdo do highway) ─
            self._draw_mult_bubble(
                hwy.center_x - hwy.bottom_hw - 36,
                hit_y - 10,
                state.effective_multiplier,
                state.star_power_active,
            )

            # ── Star Power bar (abaixo da hit line) ──────────────────────
            sp_bar_w = hwy.bottom_hw * 2
            sp_bar_h = 8
            sp_y = hit_y + 18
            sp_x = hwy.center_x - hwy.bottom_hw
            pygame.draw.rect(self.screen, (18, 18, 30),
                             (sp_x, sp_y, sp_bar_w, sp_bar_h), border_radius=4)
            fill_w = int(sp_bar_w * state.star_power_charge)
            if fill_w > 0:
                bar_color = COLOR_SP_ACTIVE if state.star_power_active else COLOR_SP_BAR
                pygame.draw.rect(self.screen, bar_color,
                                 (sp_x, sp_y, fill_w, sp_bar_h), border_radius=4)
                if state.star_power_charge >= 0.5:
                    # Glow quando cheio suficiente para ativar
                    gs = pygame.Surface((sp_bar_w + 4, sp_bar_h + 4), pygame.SRCALPHA)
                    pygame.draw.rect(gs, (*COLOR_SP_BAR, 60), (0, 0, fill_w + 4, sp_bar_h + 4), border_radius=5)
                    self.screen.blit(gs, (sp_x - 2, sp_y - 2))

            # SP label
            if state.star_power_active:
                draw_text(self.screen, "★ STAR POWER",
                          hwy.center_x, sp_y + sp_bar_h + 8,
                          size=12, color=COLOR_SP_ACTIVE, center_x=True, bold=True)

            # ── Streak (canto inferior direito) ──────────────────────────
            if state.streak >= 5:
                draw_text(self.screen,
                          f"🔥 {state.streak}",
                          hwy.center_x + hwy.bottom_hw + 36, hit_y - 10,
                          size=FONT_SMALL_SIZE, bold=True, color=(255, 140, 40),
                          center_x=True, center_y=True)

            # ── Accuracy ──────────────────────────────────────────────────
            acc_y = sp_y + sp_bar_h + 22
            if state.notes_total > 0:
                draw_text(self.screen, f"{state.accuracy_pct:.0f}%",
                          hwy.center_x, acc_y,
                          size=FONT_TINY_SIZE, color=(80, 80, 110), center_x=True)

            # Crowd meter multi-player
            if self._n_players > 1:
                self._draw_crowd_meter_single(self._crowd[i])  # reuse — move abaixo do hud

    def _draw_mult_bubble(self, cx: int, cy: int, mult: int, sp_active: bool) -> None:
        """Desenha o bubble azul de multiplicador estilo YARG."""
        r = 26
        bg_color = COLOR_MULT_SP if sp_active else COLOR_MULT_BG
        glow_color = COLOR_SP_ACTIVE if sp_active else (80, 120, 255)

        # Glow externo
        gs = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*glow_color, 60), (r + 8, r + 8), r + 6)
        self.screen.blit(gs, (cx - r - 8, cy - r - 8))

        # Círculo principal
        pygame.draw.circle(self.screen, bg_color, (cx, cy), r)
        pygame.draw.circle(self.screen, glow_color, (cx, cy), r, 2)

        # Número
        draw_text(self.screen, f"×{mult}", cx, cy,
                  size=22, bold=True, color=WHITE, center_x=True, center_y=True)

    def _draw_countdown(self) -> None:
        """Tela de countdown estilo YARG com o nome da música."""
        # Highways visíveis mas sem notas
        # Título da música
        title = getattr(self._chart.metadata, 'display_name', '') if self._chart.metadata else ''
        artist = getattr(self._chart.metadata, 'artist', '') if self._chart.metadata else ''

        # Box central com título
        box_w, box_h = 500, 100
        box_x = self.w // 2 - box_w // 2
        box_y = self.h // 2 - box_h // 2 - 60
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surf.fill((10, 10, 20, 180))
        self.screen.blit(box_surf, (box_x, box_y))
        pygame.draw.rect(self.screen, (40, 40, 80), (box_x, box_y, box_w, box_h), 1, border_radius=8)

        draw_text(self.screen, title, self.w // 2, box_y + 28,
                  size=FONT_MEDIUM_SIZE, bold=True, color=WHITE, center_x=True, center_y=True)
        draw_text(self.screen, artist, self.w // 2, box_y + 70,
                  size=FONT_SMALL_SIZE, color=(160, 160, 200), center_x=True, center_y=True)

        # Número do countdown pulsante
        n = math.ceil(self._countdown)
        if n > 0:
            pulse = 1.0 + 0.15 * math.sin(time.monotonic() * 8)
            size = int(90 * pulse)
            alpha = min(255, int(255 * (self._countdown - n + 1) * 3))
            draw_text(self.screen, str(n), self.w // 2, self.h // 2 + 30,
                      size=size, bold=True, color=COLOR_STAR, center_x=True, center_y=True, alpha=alpha)
        else:
            size = int(80 * (1.0 + 0.1 * math.sin(time.monotonic() * 12)))
            draw_text(self.screen, "GO!", self.w // 2, self.h // 2 + 30,
                      size=size, bold=True, color=(80, 255, 120), center_x=True, center_y=True)

    def _draw_pause_overlay(self) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Box de pausa
        bw, bh = 380, 160
        bx = self.w // 2 - bw // 2
        by = self.h // 2 - bh // 2
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((14, 14, 28, 220))
        self.screen.blit(box, (bx, by))
        pygame.draw.rect(self.screen, (60, 60, 120), (bx, by, bw, bh), 2, border_radius=12)

        draw_text(self.screen, "PAUSA", self.w // 2, by + 50,
                  size=52, bold=True, color=WHITE, center_x=True, center_y=True)
        draw_text(self.screen, "P — Continuar     ESC — Sair", self.w // 2, by + 108,
                  size=FONT_SMALL_SIZE, color=(120, 120, 160), center_x=True)
