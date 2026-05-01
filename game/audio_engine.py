"""
Rock Band Local — Audio Engine
Reprodução de stems, offset de latência, fade in/out.
"""
from __future__ import annotations
import os
import time
from typing import Dict, List, Optional

import pygame


STEMS = ['song', 'guitar', 'bass', 'drums', 'drums2', 'drums3', 'drums4', 'vocals', 'crowd']


class AudioEngine:
    """
    Carrega e toca os stems de uma música.
    Suporta ajuste de latência (offset_ms) e volume por stem.
    """

    def __init__(self, config: Dict):
        self.config = config
        self._channels: Dict[str, pygame.mixer.Channel] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._start_time: float = 0.0
        self._paused: bool = False
        self._pause_pos: float = 0.0
        self._loaded_folder: str = ""
        self._offset_ms: float = config.get('audio', {}).get('latency_offset_ms', 0.0)
        self._volumes = {
            'song':   config.get('audio', {}).get('song_volume', 1.0),
            'guitar': config.get('audio', {}).get('guitar_volume', 1.0),
            'bass':   config.get('audio', {}).get('bass_volume', 1.0),
            'drums':  config.get('audio', {}).get('drums_volume', 1.0),
            'drums2': config.get('audio', {}).get('drums_volume', 1.0),
            'drums3': config.get('audio', {}).get('drums_volume', 1.0),
            'drums4': config.get('audio', {}).get('drums_volume', 1.0),
            'vocals': config.get('audio', {}).get('vocals_volume', 1.0),
            'crowd':  0.5,
        }
        master = config.get('audio', {}).get('master_volume', 0.8)
        for k in self._volumes:
            self._volumes[k] *= master

        self._initialized = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            import pygame.mixer as _mx  # noqa — garante que o módulo existe
            if not _mx.get_init():
                _mx.init(frequency=44100, size=-16, channels=2, buffer=512)
            _mx.set_num_channels(16)
            self._initialized = True
        except (ImportError, NotImplementedError) as e:
            print(f"[Audio] Mixer indisponível ({e}) — rodando sem áudio.")
        except Exception as e:
            print(f"[Audio] Erro ao inicializar mixer: {e}")

    def load_song(self, folder: str, audio_streams: Dict[str, str]) -> List[str]:
        """
        Carrega os stems disponíveis. Retorna lista de stems carregados.
        """
        self.unload()
        self._loaded_folder = folder
        loaded: List[str] = []

        if not self._initialized:
            return loaded

        for stem, filename in audio_streams.items():
            filepath = os.path.join(folder, filename)
            if not os.path.exists(filepath):
                continue
            try:
                sound = pygame.mixer.Sound(filepath)
                self._sounds[stem] = sound
                loaded.append(stem)
            except Exception as e:
                print(f"[Audio] Erro ao carregar stem '{stem}': {e}")

        return loaded

    def play(self, start_ms: float = 0.0) -> None:
        """Inicia reprodução de todos os stems simultaneamente."""
        if not self._sounds:
            return

        # Calcula o offset em segundos
        offset_sec = max(0.0, start_ms / 1000.0)

        # Aloca canais e toca
        ch_idx = 0
        for stem, sound in self._sounds.items():
            ch = pygame.mixer.Channel(ch_idx)
            self._channels[stem] = ch
            vol = self._volumes.get(stem, 0.8)
            sound.set_volume(vol)
            ch.play(sound, maxtime=0)
            ch_idx += 1

        self._start_time = time.monotonic() - offset_sec
        self._paused = False

    def pause(self) -> None:
        if self._paused:
            return
        self._pause_pos = self.position_ms
        for ch in self._channels.values():
            ch.pause()
        self._paused = True

    def resume(self) -> None:
        if not self._paused:
            return
        for ch in self._channels.values():
            ch.unpause()
        self._start_time = time.monotonic() - self._pause_pos / 1000.0
        self._paused = False

    def stop(self) -> None:
        for ch in self._channels.values():
            ch.stop()
        self._channels.clear()

    def unload(self) -> None:
        self.stop()
        self._sounds.clear()

    @property
    def position_ms(self) -> float:
        """Posição atual de reprodução em ms (corrigida pelo offset de latência)."""
        if self._paused:
            return self._pause_pos
        elapsed = (time.monotonic() - self._start_time) * 1000.0
        return elapsed + self._offset_ms

    @property
    def is_playing(self) -> bool:
        return not self._paused and bool(self._channels)

    def set_stem_volume(self, stem: str, volume: float) -> None:
        self._volumes[stem] = volume
        if stem in self._sounds:
            self._sounds[stem].set_volume(volume)

    def mute_stem(self, stem: str) -> None:
        self.set_stem_volume(stem, 0.0)

    def unmute_stem(self, stem: str, volume: Optional[float] = None) -> None:
        v = volume or self._volumes.get(stem, 0.8)
        self.set_stem_volume(stem, v)

    def set_offset(self, offset_ms: float) -> None:
        self._offset_ms = offset_ms
        self.config.setdefault('audio', {})['latency_offset_ms'] = offset_ms

    @property
    def offset_ms(self) -> float:
        return self._offset_ms

    def fade_out(self, duration_ms: int = 3000) -> None:
        for ch in self._channels.values():
            ch.fadeout(duration_ms)

    # ── Countdown beep (para calibração) ──────────────────────────────────────

    def play_beep(self, freq_hz: int = 440, duration_ms: int = 100) -> None:
        """Toca um bip sintético para calibração de latência."""
        try:
            import numpy as np
            sample_rate = 44100
            t = np.linspace(0, duration_ms / 1000.0, int(sample_rate * duration_ms / 1000), endpoint=False)
            wave = (np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
            stereo = np.column_stack([wave, wave])
            sound = pygame.sndarray.make_sound(stereo)
            sound.set_volume(0.5)
            sound.play()
        except Exception:
            pass
