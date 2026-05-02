"""
Rock Band Local — Note Engine
Gerencia o highway de notas, hit detection e sustains para guitarra, baixo, bateria e vocal.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from game.chart_parser import Chart, Note, VocalPhrase
from game.scoring import Scorer, ScoreState, NoteResult
from game.constants import (
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
    HIT_PERFECT_MS, HIT_GOOD_MS, HIT_OK_MS,
    VOCAL_HIT_CENTS,
)


# ── Callbacks do engine ────────────────────────────────────────────────────────

NoteHitCB  = Callable[[Note, NoteResult], None]
NoteMissCB = Callable[[Note], None]


# ── Guitar / Bass Engine ──────────────────────────────────────────────────────

class GuitarEngine:
    """
    Gerencia hit detection para guitarra e baixo.
    Recebe eventos de fret/strum do InputManager e avança a posição de notas.
    """

    def __init__(self, notes: List[Note], scorer: Scorer, config: Dict):
        self.notes = notes
        self.scorer = scorer
        self.config = config
        self._hit_window_ok = config.get('gameplay', {}).get('hit_window_ok_ms', HIT_OK_MS)
        self._miss_ahead_ms = self._hit_window_ok + 10

        # Estado
        self._next_note_idx: int = 0
        self._active_sustains: List[Tuple[Note, float]] = []  # (note, end_time_ms)
        self._held_frets: Set[int] = set()

        # Callbacks
        self.on_hit:  Optional[NoteHitCB]  = None
        self.on_miss: Optional[NoteMissCB] = None

    def update(self, pos_ms: float) -> None:
        """Atualiza a cada frame — expira notas não tocadas."""
        # Marcar notas perdidas (passaram da janela)
        while self._next_note_idx < len(self.notes):
            note = self.notes[self._next_note_idx]
            if note.hit or note.missed:
                self._next_note_idx += 1
                continue
            if pos_ms > note.time_ms + self._miss_ahead_ms:
                note.missed = True
                result = self.scorer.miss_note()
                if self.on_miss:
                    self.on_miss(note)
                self._next_note_idx += 1
            else:
                break

        # Atualiza sustains ativos
        dt_sec = 0.016  # aprox 60fps
        active = []
        for note, end_ms in self._active_sustains:
            if pos_ms < end_ms:
                self.scorer.add_sustain_score(dt_sec)
                active.append((note, end_ms))
        self._active_sustains = active

    def on_strum(self, pos_ms: float) -> bool:
        """
        Processa uma strumada. Tenta acertar a próxima nota compatível.
        Retorna True se acertou.
        """
        note = self._find_hittable_note(pos_ms)
        if note is None:
            self.scorer.miss_note()  # overstrum
            return False
        return self._hit(note, pos_ms)

    def _find_hittable_note(self, pos_ms: float) -> Optional[Note]:
        """Procura a próxima nota dentro da janela de hit que combine com os frets segurados."""
        for i in range(self._next_note_idx, min(self._next_note_idx + 10, len(self.notes))):
            note = self.notes[i]
            if note.hit or note.missed:
                continue
            delta = abs(note.time_ms - pos_ms)
            if delta > self._hit_window_ok:
                if note.time_ms > pos_ms + self._hit_window_ok:
                    break
                continue
            # Verificar fret
            if note.fret == 5:  # nota aberta — não precisa de fret
                return note
            if note.fret in self._held_frets:
                return note
        return None

    def _hit(self, note: Note, pos_ms: float) -> bool:
        note.hit = True
        delta = pos_ms - note.time_ms
        result = self.scorer.hit_note(delta, note.is_star_power)
        if self.on_hit:
            self.on_hit(note, result)
        if note.sustain_ms > 50:
            self._active_sustains.append((note, note.end_time_ms))
        return True

    def update_frets(self, held: Set[int]) -> None:
        self._held_frets = held

    def get_visible_notes(self, pos_ms: float, window_ms: float) -> List[Note]:
        """Retorna notas na janela visual atual."""
        start = pos_ms - 200
        end   = pos_ms + window_ms
        return [n for n in self.notes if start <= n.time_ms <= end and not n.missed]


# ── Drum Engine ───────────────────────────────────────────────────────────────

class DrumEngine:
    """Hit detection para bateria (5 pads)."""

    def __init__(self, notes: List[Note], scorer: Scorer, config: Dict):
        self.notes = notes
        self.scorer = scorer
        self.config = config
        self._hit_window_ok = config.get('gameplay', {}).get('hit_window_ok_ms', HIT_OK_MS)
        self._miss_ahead_ms = self._hit_window_ok + 10
        self._next_note_idx = 0
        self.on_hit:  Optional[NoteHitCB]  = None
        self.on_miss: Optional[NoteMissCB] = None

    def update(self, pos_ms: float) -> None:
        while self._next_note_idx < len(self.notes):
            note = self.notes[self._next_note_idx]
            if note.hit or note.missed:
                self._next_note_idx += 1
                continue
            if pos_ms > note.time_ms + self._miss_ahead_ms:
                note.missed = True
                self.scorer.miss_note()
                if self.on_miss:
                    self.on_miss(note)
                self._next_note_idx += 1
            else:
                break

    def on_pad_hit(self, pad: int, pos_ms: float) -> bool:
        """pad: 0=kick, 1=red, 2=yellow, 3=blue, 4=green."""
        for i in range(self._next_note_idx, min(self._next_note_idx + 8, len(self.notes))):
            note = self.notes[i]
            if note.hit or note.missed:
                continue
            if note.fret != pad:
                continue
            delta = abs(note.time_ms - pos_ms)
            if delta <= self._hit_window_ok:
                note.hit = True
                signed_delta = pos_ms - note.time_ms
                result = self.scorer.hit_note(signed_delta, note.is_star_power)
                if self.on_hit:
                    self.on_hit(note, result)
                return True
        return False

    def get_visible_notes(self, pos_ms: float, window_ms: float) -> List[Note]:
        start = pos_ms - 200
        end   = pos_ms + window_ms
        return [n for n in self.notes if start <= n.time_ms <= end and not n.missed]


# ── Vocal Engine ──────────────────────────────────────────────────────────────

class VocalEngine:
    """Detecção de acerto por pitch para vocais."""

    def __init__(self, phrases: List[VocalPhrase], scorer: Scorer, config: Dict):
        self.phrases = phrases
        self.scorer  = scorer
        self.config  = config
        self._current_phrase_idx = 0
        self._phrase_hit_samples = 0
        self._phrase_total_samples = 0
        self.on_phrase_complete: Optional[Callable[[VocalPhrase, float], None]] = None

    def update(self, pos_ms: float, pitch_hz: float, confidence: float) -> None:
        if not self.phrases:
            return
        while self._current_phrase_idx < len(self.phrases):
            phrase = self.phrases[self._current_phrase_idx]
            if pos_ms < phrase.time_ms:
                break
            if pos_ms <= phrase.time_ms + phrase.duration_ms:
                # Dentro da frase
                self._phrase_total_samples += 1
                if confidence > 0.7 and phrase.pitch > 0:
                    if self._pitch_match(pitch_hz, phrase.pitch):
                        self._phrase_hit_samples += 1
                break
            else:
                # Frase terminou
                ratio = (
                    self._phrase_hit_samples / self._phrase_total_samples
                    if self._phrase_total_samples > 0 else 0.0
                )
                if ratio >= 0.5:
                    self.scorer.hit_note(0, False)
                else:
                    self.scorer.miss_note()
                if self.on_phrase_complete:
                    self.on_phrase_complete(phrase, ratio)
                self._current_phrase_idx += 1
                self._phrase_hit_samples = 0
                self._phrase_total_samples = 0

    @staticmethod
    def _pitch_match(sung: float, target: float) -> bool:
        if sung <= 0 or target <= 0:
            return False
        import math
        cents = abs(1200 * math.log2(sung / target))
        return cents <= VOCAL_HIT_CENTS

    def get_current_phrase(self, pos_ms: float) -> Optional[VocalPhrase]:
        if self._current_phrase_idx < len(self.phrases):
            p = self.phrases[self._current_phrase_idx]
            if p.time_ms <= pos_ms <= p.time_ms + p.duration_ms:
                return p
        return None


# ── GameSession — agrega tudo ─────────────────────────────────────────────────

@dataclass
class PlayerSession:
    player_idx: int
    instrument: str
    difficulty: str
    scorer: Scorer
    guitar_engine: Optional[GuitarEngine] = None
    drum_engine:   Optional[DrumEngine]   = None
    vocal_engine:  Optional[VocalEngine]  = None

    # Estado de display
    last_hit_feedback: str = ""          # 'perfect', 'good', 'ok', 'miss'
    last_hit_time_ms: float = 0.0
    sp_flash_end_ms: float = 0.0         # para animação de ativar SP


class GameSession:
    """
    Sessão de jogo completa com suporte a múltiplos jogadores.
    """

    def __init__(self, chart: Chart, player_configs: List[Dict], config: Dict):
        self.chart = chart
        self.config = config
        self.sessions: List[PlayerSession] = []
        self._setup_players(player_configs)

    def _setup_players(self, player_configs: List[Dict]) -> None:
        for idx, pcfg in enumerate(player_configs):
            instrument = pcfg.get('instrument', INSTRUMENT_GUITAR)
            difficulty = pcfg.get('difficulty', 'medium')

            notes = self.chart.get_notes(instrument, difficulty)
            score_state = ScoreState(notes_total=len(notes))
            scorer = Scorer(score_state)

            session = PlayerSession(
                player_idx=idx,
                instrument=instrument,
                difficulty=difficulty,
                scorer=scorer,
            )

            if instrument in (INSTRUMENT_GUITAR, INSTRUMENT_BASS):
                engine = GuitarEngine(notes, scorer, self.config)
                engine.on_hit  = lambda n, r, s=session: self._on_hit(s, n, r)
                engine.on_miss = lambda n, s=session: self._on_miss(s, n)
                session.guitar_engine = engine

            elif instrument == INSTRUMENT_DRUMS:
                engine = DrumEngine(notes, scorer, self.config)
                engine.on_hit  = lambda n, r, s=session: self._on_hit(s, n, r)
                engine.on_miss = lambda n, s=session: self._on_miss(s, n)
                session.drum_engine = engine

            elif instrument == INSTRUMENT_VOCALS:
                session.vocal_engine = VocalEngine(
                    self.chart.vocal_phrases, scorer, self.config
                )

            self.sessions.append(session)

    def _on_hit(self, session: PlayerSession, note: Note, result: NoteResult) -> None:
        session.last_hit_feedback = result.accuracy
        session.last_hit_time_ms  = time.monotonic() * 1000

    def _on_miss(self, session: PlayerSession, note: Note) -> None:
        session.last_hit_feedback = 'miss'
        session.last_hit_time_ms  = time.monotonic() * 1000

    def update(self, pos_ms: float) -> None:
        for session in self.sessions:
            if session.guitar_engine:
                session.guitar_engine.update(pos_ms)
            if session.drum_engine:
                session.drum_engine.update(pos_ms)

    def on_strum(self, player_idx: int, pos_ms: float) -> None:
        if player_idx < len(self.sessions):
            s = self.sessions[player_idx]
            if s.guitar_engine:
                s.guitar_engine.on_strum(pos_ms)

    def on_pad(self, player_idx: int, pad: int, pos_ms: float) -> None:
        if player_idx < len(self.sessions):
            s = self.sessions[player_idx]
            if s.drum_engine:
                s.drum_engine.on_pad_hit(pad, pos_ms)

    def on_frets_changed(self, player_idx: int, held_frets: Set[int]) -> None:
        if player_idx < len(self.sessions):
            s = self.sessions[player_idx]
            if s.guitar_engine:
                s.guitar_engine.update_frets(held_frets)

    def on_vocal_pitch(self, player_idx: int, pitch_hz: float, confidence: float, pos_ms: float) -> None:
        if player_idx < len(self.sessions):
            s = self.sessions[player_idx]
            if s.vocal_engine:
                s.vocal_engine.update(pos_ms, pitch_hz, confidence)

    def on_star_power(self, player_idx: int) -> None:
        if player_idx < len(self.sessions):
            s = self.sessions[player_idx]
            if s.scorer.activate_star_power():
                s.sp_flash_end_ms = time.monotonic() * 1000 + 500

    def update_star_power(self, dt_seconds: float) -> None:
        for session in self.sessions:
            session.scorer.update_star_power(dt_seconds)

    def get_visible_notes(self, player_idx: int, pos_ms: float, window_ms: float) -> List[Note]:
        if player_idx >= len(self.sessions):
            return []
        s = self.sessions[player_idx]
        if s.guitar_engine:
            return s.guitar_engine.get_visible_notes(pos_ms, window_ms)
        if s.drum_engine:
            return s.drum_engine.get_visible_notes(pos_ms, window_ms)
        return []
