"""
Rock Band Local — Scoring System
Multiplicador, Star Power, streak, FC tracking.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from game.constants import (
    NOTE_BASE_SCORE, MAX_MULTIPLIER, NOTES_PER_MULT, STAR_POWER_MULT,
    MULT_THRESHOLDS, SUSTAIN_SCORE_PPS,
)


@dataclass
class NoteResult:
    accuracy: str      # 'perfect', 'great', 'good', 'ok', 'miss'
    points: int
    multiplier: int
    time_delta_ms: float = 0.0  # diferença em ms (positivo = tardio)


@dataclass
class ScoreState:
    """Estado de score completo para um jogador."""
    score: int = 0
    streak: int = 0
    max_streak: int = 0
    notes_hit: int = 0
    notes_missed: int = 0
    notes_total: int = 0
    sustain_score: int = 0

    # Multiplicador
    multiplier: int = 1
    notes_in_current_mult: int = 0

    # Star Power
    star_power_phrases: int = 0          # frases SP capturadas
    star_power_active: bool = False
    star_power_charge: float = 0.0       # 0.0 – 1.0
    star_power_drain_rate: float = 0.25  # drena em 4 seg se não recarregar
    star_power_gain_per_phrase: float = 0.5

    # Full combo flag
    full_combo: bool = True

    # Histórico para grade final
    results: List[NoteResult] = field(default_factory=list)

    # Pontuação de referência para estrelas
    notes_perfect: int = 0
    notes_good: int    = 0
    notes_ok: int      = 0

    @property
    def effective_multiplier(self) -> int:
        m = self.multiplier
        if self.star_power_active:
            m *= STAR_POWER_MULT
        return m

    @property
    def accuracy_pct(self) -> float:
        total = self.notes_hit + self.notes_missed
        return (self.notes_hit / total * 100.0) if total > 0 else 0.0

    @property
    def stars(self) -> int:
        """Calcula 0-5 estrelas baseado em score + accuracy."""
        if self.notes_total == 0:
            return 0
        pct = self.accuracy_pct
        if self.full_combo:
            return 6  # Gold FC
        if pct >= 95:
            return 5
        if pct >= 85:
            return 4
        if pct >= 70:
            return 3
        if pct >= 50:
            return 2
        if pct >= 30:
            return 1
        return 0

    def reset(self, notes_total: int = 0) -> None:
        self.score = 0
        self.streak = 0
        self.max_streak = 0
        self.notes_hit = 0
        self.notes_missed = 0
        self.notes_total = notes_total
        self.sustain_score = 0
        self.multiplier = 1
        self.notes_in_current_mult = 0
        self.star_power_phrases = 0
        self.star_power_active = False
        self.star_power_charge = 0.0
        self.full_combo = True
        self.results.clear()
        self.notes_perfect = 0
        self.notes_good = 0
        self.notes_ok = 0


class Scorer:
    """Processa acertos/erros e mantém o ScoreState."""

    def __init__(self, state: Optional[ScoreState] = None):
        self.state = state or ScoreState()

    def hit_note(self, delta_ms: float, is_star_power_phrase: bool = False) -> NoteResult:
        """Registra um acerto. delta_ms = |tempo_real - tempo_alvo|."""
        s = self.state
        abs_delta = abs(delta_ms)

        if abs_delta <= 20:
            accuracy = 'perfect'
            s.notes_perfect += 1
        elif abs_delta <= 35:
            accuracy = 'great'
            s.notes_good += 1
        elif abs_delta <= 45:
            accuracy = 'good'
            s.notes_good += 1
        else:
            accuracy = 'ok'
            s.notes_ok += 1

        # Streak e multiplicador
        s.streak += 1
        s.notes_hit += 1
        s.max_streak = max(s.max_streak, s.streak)
        s.notes_in_current_mult += 1

        # Avança multiplicador a cada NOTES_PER_MULT acertos consecutivos
        if s.multiplier < MAX_MULTIPLIER and s.notes_in_current_mult >= NOTES_PER_MULT:
            s.multiplier = min(s.multiplier + 1, MAX_MULTIPLIER)
            s.notes_in_current_mult = 0

        # Star Power: phrase completa adiciona carga
        if is_star_power_phrase:
            s.star_power_phrases += 1
            s.star_power_charge = min(1.0, s.star_power_charge + s.star_power_gain_per_phrase)

        points = NOTE_BASE_SCORE * s.effective_multiplier
        s.score += points

        result = NoteResult(
            accuracy=accuracy,
            points=points,
            multiplier=s.effective_multiplier,
            time_delta_ms=delta_ms,
        )
        s.results.append(result)
        return result

    def miss_note(self) -> NoteResult:
        """Registra um erro."""
        s = self.state
        s.streak = 0
        s.notes_missed += 1
        s.notes_in_current_mult = 0
        s.multiplier = 1
        s.full_combo = False

        result = NoteResult(accuracy='miss', points=0, multiplier=1)
        s.results.append(result)
        return result

    def add_sustain_score(self, dt_seconds: float) -> int:
        """Adiciona pontos de sustain baseado no tempo segurado."""
        if dt_seconds <= 0:
            return 0
        s = self.state
        raw_pts = SUSTAIN_SCORE_PPS * dt_seconds * s.effective_multiplier
        pts = int(raw_pts)
        s.score += pts
        s.sustain_score += pts
        return pts

    def activate_star_power(self) -> bool:
        """Tenta ativar Star Power. Retorna True se ativado."""
        s = self.state
        if s.star_power_active or s.star_power_charge < 0.5:
            return False
        s.star_power_active = True
        return True

    def update_star_power(self, dt_seconds: float) -> None:
        """Atualiza drain do Star Power (chamado a cada frame)."""
        s = self.state
        if not s.star_power_active:
            return
        s.star_power_charge -= s.star_power_drain_rate * dt_seconds
        if s.star_power_charge <= 0.0:
            s.star_power_charge = 0.0
            s.star_power_active = False

    def get_grade_letter(self) -> str:
        pct = self.state.accuracy_pct
        if pct >= 100:
            return 'SSS'
        if pct >= 95:
            return 'SS'
        if pct >= 90:
            return 'S'
        if pct >= 80:
            return 'A'
        if pct >= 70:
            return 'B'
        if pct >= 60:
            return 'C'
        if pct >= 50:
            return 'D'
        return 'F'
