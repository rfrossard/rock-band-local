"""
Rock Band Local — Chart Parser
Suporta formato .chart (Clone Hero / GH) e .mid (MIDI básico).
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.constants import (
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
    DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT,
    CHART_TRACK,
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Note:
    """Uma nota no highway."""
    tick: int           # posição em ticks
    time_ms: float      # tempo em ms (calculado a partir do BPM)
    fret: int           # 0-4 (guitarra/baixo), 0-4 (bateria), 5=aberta
    sustain_ticks: int = 0
    sustain_ms: float  = 0.0
    is_star_power: bool = False
    hopo: bool = False
    hit: bool = False
    missed: bool = False

    @property
    def end_time_ms(self) -> float:
        return self.time_ms + self.sustain_ms


@dataclass
class VocalPhrase:
    """Frase vocal com tom alvo."""
    tick: int
    time_ms: float
    duration_ticks: int
    duration_ms: float
    lyric: str
    pitch: float = 0.0     # Hz — 0 se for unpitched


@dataclass
class BpmEvent:
    tick: int
    bpm: float


@dataclass
class TimeSignature:
    tick: int
    numerator: int
    denominator: int


@dataclass
class SongMetadata:
    name: str = "Unknown"
    artist: str = "Unknown"
    album: str = ""
    year: str = ""
    charter: str = ""
    genre: str = ""
    difficulty_guitar: int = 0
    difficulty_bass: int = 0
    difficulty_drums: int = 0
    offset_ms: float = 0.0
    preview_start_ms: float = 0.0
    preview_end_ms: float = 0.0
    audio_streams: Dict[str, str] = field(default_factory=dict)  # stem_name -> filename

    @property
    def display_name(self) -> str:
        if self.artist and self.artist != "Unknown":
            return f"{self.artist} – {self.name}"
        return self.name


@dataclass
class Chart:
    metadata: SongMetadata
    bpm_events: List[BpmEvent]
    time_signatures: List[TimeSignature]
    tracks: Dict[str, List[Note]]         # key = (instrument, difficulty) str
    vocal_phrases: List[VocalPhrase]
    resolution: int = 192                 # ticks por beat

    def get_notes(self, instrument: str, difficulty: str) -> List[Note]:
        key = f"{instrument}_{difficulty}"
        return self.tracks.get(key, [])

    @property
    def duration_ms(self) -> float:
        """Duração estimada da música em ms."""
        all_notes = [n for notes in self.tracks.values() for n in notes]
        if not all_notes:
            return 0.0
        return max(n.end_time_ms for n in all_notes) + 500.0


# ── BPM / tick ────────────────────────────────────────────────────────────────

def ticks_to_ms(tick: int, bpm_events: List[BpmEvent], resolution: int) -> float:
    """Converte ticks em milissegundos usando a lista de eventos de BPM."""
    if not bpm_events:
        return tick / resolution * (60000.0 / 120.0)

    ms = 0.0
    current_bpm = bpm_events[0].bpm
    current_tick = 0

    for event in bpm_events:
        if event.tick >= tick:
            break
        delta_ticks = event.tick - current_tick
        ms += delta_ticks / resolution * (60000.0 / current_bpm)
        current_bpm = event.bpm
        current_tick = event.tick

    remaining = tick - current_tick
    ms += remaining / resolution * (60000.0 / current_bpm)
    return ms


# ── .chart parser ─────────────────────────────────────────────────────────────

def _parse_song_section(lines: List[str]) -> SongMetadata:
    meta = SongMetadata()
    audio_streams: Dict[str, str] = {}

    stem_keys = {
        "MusicStream": "song",
        "GuitarStream": "guitar",
        "BassStream": "bass",
        "RhythmStream": "rhythm",
        "DrumStream": "drums",
        "Drum2Stream": "drums2",
        "Drum3Stream": "drums3",
        "Drum4Stream": "drums4",
        "VocalStream": "vocals",
        "CrowdStream": "crowd",
    }

    for line in lines:
        line = line.strip()
        if not line or line in ('{', '}'):
            continue
        if '=' not in line:
            continue
        key, _, val = line.partition('=')
        key = key.strip()
        val = val.strip().strip('"')

        if key == "Name":
            meta.name = val
        elif key == "Artist":
            meta.artist = val
        elif key == "Album":
            meta.album = val
        elif key == "Year":
            meta.year = val.lstrip(', ')
        elif key == "Charter":
            meta.charter = val
        elif key == "Genre":
            meta.genre = val
        elif key == "Offset":
            try:
                meta.offset_ms = float(val) * 1000.0
            except ValueError:
                pass
        elif key == "PreviewStart":
            try:
                meta.preview_start_ms = float(val) * 1000.0
            except ValueError:
                pass
        elif key == "PreviewEnd":
            try:
                meta.preview_end_ms = float(val) * 1000.0
            except ValueError:
                pass
        elif key in stem_keys:
            audio_streams[stem_keys[key]] = val

    meta.audio_streams = audio_streams
    return meta


def _parse_sync_section(lines: List[str]) -> Tuple[List[BpmEvent], List[TimeSignature]]:
    bpms: List[BpmEvent] = []
    ts_list: List[TimeSignature] = []

    for line in lines:
        line = line.strip()
        if not line or line in ('{', '}'):
            continue
        m = re.match(r'(\d+)\s*=\s*([A-Z]+)\s+(.+)', line)
        if not m:
            continue
        tick = int(m.group(1))
        event_type = m.group(2)
        args = m.group(3).split()

        if event_type == 'B':
            # BPM em millibeats (ex: 120000 = 120.000 BPM)
            bpm = int(args[0]) / 1000.0
            bpms.append(BpmEvent(tick=tick, bpm=bpm))
        elif event_type == 'TS':
            num = int(args[0])
            den = int(args[1]) if len(args) > 1 else 4
            ts_list.append(TimeSignature(tick=tick, numerator=num, denominator=den))

    bpms.sort(key=lambda e: e.tick)
    return bpms, ts_list


def _parse_note_section(
    lines: List[str],
    bpm_events: List[BpmEvent],
    resolution: int,
    is_drums: bool = False,
) -> List[Note]:
    notes: List[Note] = []
    star_power_ranges: List[Tuple[int, int]] = []  # (start_tick, end_tick)

    raw_notes: Dict[int, List[Tuple[int, int]]] = {}  # tick -> [(fret, sustain)]

    for line in lines:
        line = line.strip()
        if not line or line in ('{', '}'):
            continue
        m = re.match(r'(\d+)\s*=\s*([A-Z]+)\s+(.+)', line)
        if not m:
            continue
        tick = int(m.group(1))
        event_type = m.group(2)
        args = m.group(3).split()

        if event_type == 'N':
            fret = int(args[0])
            sustain = int(args[1]) if len(args) > 1 else 0
            if tick not in raw_notes:
                raw_notes[tick] = []
            raw_notes[tick].append((fret, sustain))
        elif event_type == 'S':
            s_type = int(args[0])
            s_len  = int(args[1]) if len(args) > 1 else 0
            if s_type == 2:  # Star Power phrase
                star_power_ranges.append((tick, tick + s_len))

    def _in_star_power(t: int) -> bool:
        return any(s <= t < e for s, e in star_power_ranges)

    for tick in sorted(raw_notes.keys()):
        fret_sustains = raw_notes[tick]
        time_ms = ticks_to_ms(tick, bpm_events, resolution)
        for fret, sustain in fret_sustains:
            sustain_ms = ticks_to_ms(tick + sustain, bpm_events, resolution) - time_ms if sustain > 0 else 0.0
            note = Note(
                tick=tick,
                time_ms=time_ms,
                fret=fret,
                sustain_ticks=sustain,
                sustain_ms=sustain_ms,
                is_star_power=_in_star_power(tick),
            )
            notes.append(note)

    notes.sort(key=lambda n: (n.time_ms, n.fret))
    return notes


def _parse_vocals_section(
    lines: List[str],
    bpm_events: List[BpmEvent],
    resolution: int,
) -> List[VocalPhrase]:
    phrases: List[VocalPhrase] = []

    for line in lines:
        line = line.strip()
        if not line or line in ('{', '}'):
            continue
        m = re.match(r'(\d+)\s*=\s*([A-Z]+)\s+(.+)', line)
        if not m:
            continue
        tick = int(m.group(1))
        event_type = m.group(2)
        args_str = m.group(3)

        if event_type == 'N':
            args = args_str.split()
            fret = int(args[0])
            sustain = int(args[1]) if len(args) > 1 else 0
            time_ms = ticks_to_ms(tick, bpm_events, resolution)
            dur_ms  = ticks_to_ms(tick + sustain, bpm_events, resolution) - time_ms
            phrases.append(VocalPhrase(
                tick=tick,
                time_ms=time_ms,
                duration_ticks=sustain,
                duration_ms=dur_ms,
                lyric="",
                pitch=0.0,
            ))
        elif event_type == 'E':
            # Lyric events
            lyric = args_str.strip('"').replace('+', '').strip()
            # Find the phrase at this tick
            for p in reversed(phrases):
                if p.tick == tick:
                    p.lyric = lyric
                    break

    return phrases


def parse_chart_file(filepath: str) -> Optional[Chart]:
    """Parse um arquivo .chart e retorna um objeto Chart."""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
            content = f.read()
    except OSError:
        return None

    # Dividir em seções
    sections: Dict[str, List[str]] = {}
    current_section = None
    current_lines: List[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if current_section:
                sections[current_section] = current_lines
            current_section = stripped[1:-1]
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    if current_section:
        sections[current_section] = current_lines

    # Metadata
    metadata = _parse_song_section(sections.get('Song', []))

    # Resolution
    resolution = 192
    for line in sections.get('Song', []):
        m = re.match(r'\s*Resolution\s*=\s*(\d+)', line)
        if m:
            resolution = int(m.group(1))
            break

    # Sync Track
    bpm_events, time_signatures = _parse_sync_section(sections.get('SyncTrack', []))
    if not bpm_events:
        bpm_events = [BpmEvent(tick=0, bpm=120.0)]

    # Tracks
    tracks: Dict[str, List[Note]] = {}
    vocal_phrases: List[VocalPhrase] = []

    for instrument in (INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS):
        for difficulty in (DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT):
            section_name = CHART_TRACK.get((instrument, difficulty))
            if section_name and section_name in sections:
                is_drums = (instrument == INSTRUMENT_DRUMS)
                notes = _parse_note_section(
                    sections[section_name], bpm_events, resolution, is_drums
                )
                key = f"{instrument}_{difficulty}"
                tracks[key] = notes

    # Vocals
    for diff in (DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT):
        section_name = CHART_TRACK.get((INSTRUMENT_VOCALS, diff))
        if section_name and section_name in sections:
            vocal_phrases = _parse_vocals_section(sections[section_name], bpm_events, resolution)
            break

    return Chart(
        metadata=metadata,
        bpm_events=bpm_events,
        time_signatures=time_signatures,
        tracks=tracks,
        vocal_phrases=vocal_phrases,
        resolution=resolution,
    )


# ── Song discovery ─────────────────────────────────────────────────────────────

def discover_songs(songs_dir: str) -> List[Tuple[str, Chart]]:
    """
    Percorre songs_dir buscando arquivos notes.chart (ou song.chart).
    Retorna lista de (song_folder_path, Chart).
    """
    results: List[Tuple[str, Chart]] = []

    if not os.path.isdir(songs_dir):
        os.makedirs(songs_dir, exist_ok=True)
        return results

    for entry in sorted(os.scandir(songs_dir), key=lambda e: e.name.lower()):
        if not entry.is_dir():
            continue
        for chart_name in ('notes.chart', 'song.chart', 'notes.mid'):
            chart_path = os.path.join(entry.path, chart_name)
            if os.path.exists(chart_path):
                if chart_name.endswith('.chart'):
                    chart = parse_chart_file(chart_path)
                else:
                    chart = _parse_midi_stub(chart_path, entry.path)
                if chart:
                    # Preencher audio_streams com os arquivos existentes
                    _resolve_audio_streams(chart.metadata, entry.path)
                    results.append((entry.path, chart))
                break

    return results


def _resolve_audio_streams(meta: SongMetadata, folder: str) -> None:
    """Detecta os arquivos de áudio na pasta e atualiza audio_streams."""
    audio_exts = ('.ogg', '.mp3', '.wav', '.opus')
    stem_candidates = {
        'guitar': ('guitar', 'guitar.ogg', 'guitar.mp3'),
        'bass':   ('bass', 'rhythm', 'bass.ogg', 'rhythm.ogg'),
        'drums':  ('drums', 'drums.ogg', 'drums_1.ogg'),
        'vocals': ('vocals', 'vocals.ogg'),
        'song':   ('song', 'song.ogg', 'music.ogg', 'backing.ogg'),
        'crowd':  ('crowd', 'crowd.ogg'),
    }
    existing = {f.lower(): f for f in os.listdir(folder)}

    for stem, candidates in stem_candidates.items():
        if stem in meta.audio_streams and os.path.exists(
            os.path.join(folder, meta.audio_streams[stem])
        ):
            continue
        for candidate in candidates:
            for ext in audio_exts:
                fname = candidate if candidate.endswith(ext) else candidate + ext
                if fname in existing:
                    meta.audio_streams[stem] = existing[fname]
                    break
            else:
                continue
            break


def _parse_midi_stub(midi_path: str, folder: str) -> Optional[Chart]:
    """
    Parser MIDI simplificado (stub).  Para suporte completo a MIDI instale mido:
      pip install mido
    """
    meta = SongMetadata(name=os.path.basename(folder))
    try:
        import mido  # type: ignore
        mid = mido.MidiFile(midi_path)

        bpm_events: List[BpmEvent] = [BpmEvent(tick=0, bpm=120.0)]
        resolution = mid.ticks_per_beat or 480
        tracks_dict: Dict[str, List[Note]] = {}
        vocal_phrases: List[VocalPhrase] = []

        # Detecta tempo map
        for track in mid.tracks:
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'set_tempo':
                    bpm = 60_000_000 / msg.tempo
                    bpm_events.append(BpmEvent(tick=abs_tick, bpm=bpm))

        bpm_events.sort(key=lambda e: e.tick)

        # Parse tracks de notas (simplificado para guitarra Expert)
        MIDI_GUITAR_EXPERT_START = 96
        for track in mid.tracks:
            name = track.name.lower()
            if 'guitar' not in name and 'single' not in name:
                continue
            notes_on: Dict[int, int] = {}
            note_list: List[Note] = []
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    notes_on[msg.note] = abs_tick
                elif msg.type in ('note_off', 'note_on') and msg.velocity == 0:
                    if msg.note in notes_on:
                        start = notes_on.pop(msg.note)
                        fret = msg.note - MIDI_GUITAR_EXPERT_START
                        if 0 <= fret <= 4:
                            t_ms = ticks_to_ms(start, bpm_events, resolution)
                            sus  = ticks_to_ms(abs_tick, bpm_events, resolution) - t_ms
                            note_list.append(Note(
                                tick=start, time_ms=t_ms,
                                fret=fret, sustain_ticks=abs_tick - start,
                                sustain_ms=sus,
                            ))
            if note_list:
                tracks_dict[f"{INSTRUMENT_GUITAR}_{DIFF_EXPERT}"] = sorted(
                    note_list, key=lambda n: n.time_ms
                )

        return Chart(
            metadata=meta,
            bpm_events=bpm_events,
            time_signatures=[TimeSignature(0, 4, 4)],
            tracks=tracks_dict,
            vocal_phrases=vocal_phrases,
            resolution=resolution,
        )
    except ImportError:
        # mido não instalado — retornar chart vazio
        return Chart(
            metadata=meta,
            bpm_events=[BpmEvent(0, 120.0)],
            time_signatures=[TimeSignature(0, 4, 4)],
            tracks={},
            vocal_phrases=[],
        )
    except Exception:
        return None
