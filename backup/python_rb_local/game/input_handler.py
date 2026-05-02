"""
Rock Band Local — Input Handler
Gerencia teclado, joystick (guitarra BT Rock Band PS5, bateria USB Rock Band PS5)
e microfone USB para detecção de pitch vocal.
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

import pygame
import numpy as np

from game.constants import (
    INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS,
)


# ── Eventos de input ──────────────────────────────────────────────────────────

@dataclass
class FretEvent:
    """Fret pressionado / solto."""
    player_idx: int
    fret: int        # 0-4
    pressed: bool    # True=down, False=up
    timestamp_ms: float = field(default_factory=lambda: time.monotonic() * 1000)


@dataclass
class StrumEvent:
    """Strumada (up ou down)."""
    player_idx: int
    direction: int   # +1 = down, -1 = up
    timestamp_ms: float = field(default_factory=lambda: time.monotonic() * 1000)


@dataclass
class PadEvent:
    """Pad de bateria acionado."""
    player_idx: int
    pad: int         # 0=kick, 1=red, 2=yellow, 3=blue, 4=green
    velocity: float  # 0.0-1.0
    timestamp_ms: float = field(default_factory=lambda: time.monotonic() * 1000)


@dataclass
class StarPowerEvent:
    player_idx: int
    timestamp_ms: float = field(default_factory=lambda: time.monotonic() * 1000)


@dataclass
class VocalPitchSample:
    pitch_hz: float
    confidence: float
    timestamp_ms: float = field(default_factory=lambda: time.monotonic() * 1000)


# ── Perfis de controladores Rock Band ─────────────────────────────────────────
# Cada perfil mapeia botões do joystick para ações do jogo.
# O Rock Band PS5 usa o PDP Riffmaster (Bluetooth) e o kit de bateria USB.

class RockBandGuitarProfile:
    """
    Perfil para guitarra Rock Band (Wii/PS3/PS4/PS5 via Bluetooth ou USB).
    Os mapeamentos podem variar por fabricante; use o modo de detecção automática.
    """
    # Botões padrão (podem ser ajustados na tela de configurações)
    FRET_GREEN  = 1
    FRET_RED    = 2
    FRET_YELLOW = 3
    FRET_BLUE   = 0
    FRET_ORANGE = 4

    STRUM_AXIS  = 1     # axis vertical do hat
    STAR_POWER_BTN = 8  # tilt / botão dedicado

    # Mapeamento alternativo para PDP Riffmaster PS5
    PDP_RIFFMASTER = {
        'frets': [1, 2, 3, 0, 4],  # G R Y B O
        'strum_up_btn': 10,
        'strum_down_btn': 11,
        'strum_axis': 1,
        'star_power': 8,
        'select': 6,
        'start': 7,
    }

    def __init__(self, profile: Optional[Dict] = None):
        p = profile or self.PDP_RIFFMASTER
        self.fret_buttons: List[int] = p.get('frets', [1, 2, 3, 0, 4])
        self.strum_up_btn: Optional[int] = p.get('strum_up_btn')
        self.strum_down_btn: Optional[int] = p.get('strum_down_btn')
        self.strum_axis: int = p.get('strum_axis', 1)
        self.star_power_btn: int = p.get('star_power', 8)
        self._last_strum_axis: float = 0.0


class RockBandDrumProfile:
    """
    Perfil para bateria Rock Band PS5 (USB HID).
    Pad order: kick=0, red=1, yellow=2 (hi-hat), blue=3, green=4,
               yellow_cymbal=5, blue_cymbal=6, green_cymbal=7.
    """
    PS5_DRUM = {
        'kick': 0,
        'red': 1,
        'yellow_pad': 2,
        'blue_pad': 3,
        'green_pad': 4,
        'yellow_cymbal': 5,
        'blue_cymbal': 6,
        'green_cymbal': 7,
        'start': 9,
        'select': 8,
    }

    def __init__(self, profile: Optional[Dict] = None):
        p = profile or self.PS5_DRUM
        self.kick_btn: int          = p.get('kick', 0)
        self.red_btn: int           = p.get('red', 1)
        self.yellow_pad_btn: int    = p.get('yellow_pad', 2)
        self.blue_pad_btn: int      = p.get('blue_pad', 3)
        self.green_pad_btn: int     = p.get('green_pad', 4)
        self.yellow_cymbal_btn: int = p.get('yellow_cymbal', 5)
        self.blue_cymbal_btn: int   = p.get('blue_cymbal', 6)
        self.green_cymbal_btn: int  = p.get('green_cymbal', 7)

    def pad_for_button(self, btn: int) -> Optional[int]:
        """Retorna índice de pad (0-4) ou None se não for um pad."""
        m = {
            self.kick_btn: 0,
            self.red_btn: 1,
            self.yellow_pad_btn: 2,
            self.yellow_cymbal_btn: 2,
            self.blue_pad_btn: 3,
            self.blue_cymbal_btn: 3,
            self.green_pad_btn: 4,
            self.green_cymbal_btn: 4,
        }
        return m.get(btn)


# ── Player input state ─────────────────────────────────────────────────────────

class PlayerInput:
    """Estado de input para um jogador."""

    def __init__(self, player_idx: int, instrument: str, config: Dict):
        self.player_idx = player_idx
        self.instrument = instrument
        self.config = config
        self.held_frets: Set[int] = set()
        self.last_vocal_pitch: Optional[VocalPitchSample] = None

        # Callbacks
        self.on_fret:        Optional[Callable[[FretEvent], None]]       = None
        self.on_strum:       Optional[Callable[[StrumEvent], None]]      = None
        self.on_pad:         Optional[Callable[[PadEvent], None]]        = None
        self.on_star_power:  Optional[Callable[[StarPowerEvent], None]]  = None

        # Perfis de joystick
        self.guitar_profile = RockBandGuitarProfile()
        self.drum_profile   = RockBandDrumProfile()
        self.joystick: Optional[pygame.joystick.JoystickType] = None  # type: ignore

    def fire_fret(self, fret: int, pressed: bool) -> None:
        if pressed:
            self.held_frets.add(fret)
        else:
            self.held_frets.discard(fret)
        if self.on_fret:
            self.on_fret(FretEvent(self.player_idx, fret, pressed))

    def fire_strum(self, direction: int) -> None:
        if self.on_strum:
            self.on_strum(StrumEvent(self.player_idx, direction))

    def fire_pad(self, pad: int, velocity: float = 1.0) -> None:
        if self.on_pad:
            self.on_pad(PadEvent(self.player_idx, pad, velocity))

    def fire_star_power(self) -> None:
        if self.on_star_power:
            self.on_star_power(StarPowerEvent(self.player_idx))


# ── Keyboard mapping ───────────────────────────────────────────────────────────

DEFAULT_KEYBOARD_GUITAR = {
    'frets': [pygame.K_s, pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k],
    'strum_down': pygame.K_DOWN,
    'strum_up':   pygame.K_UP,
    'star_power': pygame.K_SPACE,
}

DEFAULT_KEYBOARD_GUITAR_P2 = {
    'frets': [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5],
    'strum_down': pygame.K_RETURN,
    'strum_up':   pygame.K_RSHIFT,
    'star_power': pygame.K_BACKSPACE,
}

DEFAULT_KEYBOARD_DRUMS = {
    'pads': [pygame.K_v, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_j],
    # kick, red, yellow, blue, green
}


# ── Mic pitch detector ─────────────────────────────────────────────────────────

class MicPitchDetector:
    """
    Detecta pitch em tempo real via microfone usando aubio.
    Roda em thread separada para não bloquear o game loop.
    """

    def __init__(self, device_index: Optional[int] = None, sample_rate: int = 44100):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.buf_size = 2048
        self.hop_size = 512
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.latest_sample: Optional[VocalPitchSample] = None
        self._lock = threading.Lock()
        self._available = False
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        try:
            import sounddevice   # noqa: F401
            import aubio         # noqa: F401
            self._available = True
        except ImportError:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def start(self) -> bool:
        if not self._available or self._running:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_latest(self) -> Optional[VocalPitchSample]:
        with self._lock:
            return self.latest_sample

    def _run(self) -> None:
        try:
            import sounddevice as sd
            import aubio

            pitch_detector = aubio.pitch(
                "yin",
                self.buf_size,
                self.hop_size,
                self.sample_rate,
            )
            pitch_detector.set_unit("Hz")
            pitch_detector.set_silence(-40)

            def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
                if not self._running:
                    raise sd.CallbackStop()
                samples = indata[:, 0].astype(np.float32)
                pitch_hz   = float(pitch_detector(samples)[0])
                confidence = float(pitch_detector.get_confidence())
                with self._lock:
                    self.latest_sample = VocalPitchSample(
                        pitch_hz=pitch_hz,
                        confidence=confidence,
                    )

            with sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.hop_size,
                dtype='float32',
                channels=1,
                device=self.device_index,
                callback=callback,
            ):
                while self._running:
                    time.sleep(0.01)

        except Exception as e:
            print(f"[Mic] Erro no detector de pitch: {e}")
            self._running = False


# ── Central InputManager ───────────────────────────────────────────────────────

class InputManager:
    """
    Gerencia todos os jogadores, joysticks e microfone.
    Deve ser chamado a cada frame com process_events(pygame_events).
    """

    def __init__(self, config: Dict):
        self.config = config
        self.players: List[PlayerInput] = []
        self._keyboard_guitar_map: Dict[int, Tuple[int, str]] = {}
        # key=pygame_key -> (player_idx, 'fret_N' | 'strum_up' | 'strum_down' | 'star_power')
        self.mic_detector: Optional[MicPitchDetector] = None
        self._joysticks: Dict[int, pygame.joystick.JoystickType] = {}  # type: ignore
        self._guitar_js_ids: Dict[int, int] = {}  # joystick_id -> player_idx
        self._drums_js_ids:  Dict[int, int] = {}
        self._strum_axis_prev: Dict[int, float] = {}

    def setup_players(self, player_configs: List[Dict]) -> None:
        """Configura jogadores a partir da lista de configs."""
        self.players.clear()
        self._keyboard_guitar_map.clear()
        self._guitar_js_ids.clear()
        self._drums_js_ids.clear()

        pygame.joystick.init()
        n_joysticks = pygame.joystick.get_count()
        js_list = []
        for i in range(n_joysticks):
            js = pygame.joystick.Joystick(i)
            js.init()
            js_list.append(js)
            self._joysticks[i] = js

        guitar_js_idx = 0
        drums_js_idx  = 0

        for idx, pcfg in enumerate(player_configs):
            instrument = pcfg.get('instrument', INSTRUMENT_GUITAR)
            player = PlayerInput(idx, instrument, pcfg)
            player.guitar_profile = RockBandGuitarProfile(
                pcfg.get('guitar_profile')
            )
            player.drum_profile = RockBandDrumProfile(
                pcfg.get('drum_profile')
            )

            # Atribuir joystick automaticamente por instrumento
            if instrument in (INSTRUMENT_GUITAR, INSTRUMENT_BASS):
                # Procura joystick com nome contendo "guitar" ou "rock band"
                assigned = False
                for js in js_list:
                    name = js.get_name().lower()
                    if ('guitar' in name or 'riffmaster' in name or 'rock band' in name
                            and 'drum' not in name):
                        if js.get_id() not in self._guitar_js_ids:
                            player.joystick = js
                            self._guitar_js_ids[js.get_id()] = idx
                            assigned = True
                            break
                if not assigned and guitar_js_idx < len(js_list):
                    # Atribuir o próximo joystick disponível
                    for js in js_list:
                        if (js.get_id() not in self._guitar_js_ids
                                and js.get_id() not in self._drums_js_ids):
                            player.joystick = js
                            self._guitar_js_ids[js.get_id()] = idx
                            guitar_js_idx += 1
                            break

                # Keyboard fallback
                kb_map = DEFAULT_KEYBOARD_GUITAR if idx == 0 else DEFAULT_KEYBOARD_GUITAR_P2
                for fi, key in enumerate(kb_map['frets']):
                    self._keyboard_guitar_map[key] = (idx, f'fret_{fi}')
                self._keyboard_guitar_map[kb_map['strum_down']] = (idx, 'strum_down')
                self._keyboard_guitar_map[kb_map['strum_up']]   = (idx, 'strum_up')
                self._keyboard_guitar_map[kb_map['star_power']] = (idx, 'star_power')

            elif instrument == INSTRUMENT_DRUMS:
                # Procura bateria
                for js in js_list:
                    name = js.get_name().lower()
                    if ('drum' in name or 'rock band' in name):
                        if js.get_id() not in self._drums_js_ids:
                            player.joystick = js
                            self._drums_js_ids[js.get_id()] = idx
                            break
                if player.joystick is None:
                    for js in js_list:
                        if (js.get_id() not in self._guitar_js_ids
                                and js.get_id() not in self._drums_js_ids):
                            player.joystick = js
                            self._drums_js_ids[js.get_id()] = idx
                            break

                # Keyboard para bateria
                kb = DEFAULT_KEYBOARD_DRUMS
                for pi, key in enumerate(kb['pads']):
                    self._keyboard_guitar_map[key] = (idx, f'pad_{pi}')

            elif instrument == INSTRUMENT_VOCALS:
                # Microfone
                mic_idx = pcfg.get('mic_device_index')
                if self.mic_detector is None:
                    self.mic_detector = MicPitchDetector(device_index=mic_idx)
                    self.mic_detector.start()

            self.players.append(player)

    def process_events(self, events: List[pygame.event.Event]) -> None:
        """Processa eventos do pygame a cada frame."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key, True)
            elif event.type == pygame.KEYUP:
                self._handle_key(event.key, False)
            elif event.type == pygame.JOYBUTTONDOWN:
                self._handle_joy_button(event.joy, event.button, True)
            elif event.type == pygame.JOYBUTTONUP:
                self._handle_joy_button(event.joy, event.button, False)
            elif event.type == pygame.JOYAXISMOTION:
                self._handle_joy_axis(event.joy, event.axis, event.value)
            elif event.type == pygame.JOYHATMOTION:
                self._handle_joy_hat(event.joy, event.hat, event.value)

    def _handle_key(self, key: int, pressed: bool) -> None:
        info = self._keyboard_guitar_map.get(key)
        if not info:
            return
        pidx, action = info
        if pidx >= len(self.players):
            return
        p = self.players[pidx]

        if action.startswith('fret_'):
            fret = int(action[5:])
            p.fire_fret(fret, pressed)
        elif action == 'strum_down' and pressed:
            p.fire_strum(+1)
        elif action == 'strum_up' and pressed:
            p.fire_strum(-1)
        elif action == 'star_power' and pressed:
            p.fire_star_power()
        elif action.startswith('pad_') and pressed:
            pad = int(action[4:])
            p.fire_pad(pad)

    def _handle_joy_button(self, joy_id: int, btn: int, pressed: bool) -> None:
        # Guitarra
        if joy_id in self._guitar_js_ids:
            pidx = self._guitar_js_ids[joy_id]
            p = self.players[pidx]
            prof = p.guitar_profile
            if btn in prof.fret_buttons:
                fret = prof.fret_buttons.index(btn)
                p.fire_fret(fret, pressed)
            elif btn == prof.star_power_btn and pressed:
                p.fire_star_power()
            elif prof.strum_up_btn is not None and btn == prof.strum_up_btn and pressed:
                p.fire_strum(-1)
            elif prof.strum_down_btn is not None and btn == prof.strum_down_btn and pressed:
                p.fire_strum(+1)

        # Bateria
        elif joy_id in self._drums_js_ids:
            pidx = self._drums_js_ids[joy_id]
            p = self.players[pidx]
            pad = p.drum_profile.pad_for_button(btn)
            if pad is not None and pressed:
                p.fire_pad(pad)

    def _handle_joy_axis(self, joy_id: int, axis: int, value: float) -> None:
        if joy_id not in self._guitar_js_ids:
            return
        pidx = self._guitar_js_ids[joy_id]
        p = self.players[pidx]
        prof = p.guitar_profile
        if axis == prof.strum_axis:
            prev = self._strum_axis_prev.get(joy_id, 0.0)
            if value > 0.5 and prev <= 0.5:
                p.fire_strum(+1)
            elif value < -0.5 and prev >= -0.5:
                p.fire_strum(-1)
            self._strum_axis_prev[joy_id] = value

    def _handle_joy_hat(self, joy_id: int, hat: int, value: Tuple[int, int]) -> None:
        if joy_id not in self._guitar_js_ids:
            return
        pidx = self._guitar_js_ids[joy_id]
        p = self.players[pidx]
        # Hat vertical para strum
        dx, dy = value
        if dy == -1:
            p.fire_strum(+1)
        elif dy == 1:
            p.fire_strum(-1)

    def get_vocal_pitch(self) -> Optional[VocalPitchSample]:
        if self.mic_detector:
            return self.mic_detector.get_latest()
        return None

    def shutdown(self) -> None:
        if self.mic_detector:
            self.mic_detector.stop()

    # ── Detecção automática de joysticks ──────────────────────────────────────

    @staticmethod
    def list_joysticks() -> List[Dict]:
        """Lista todos os joysticks conectados."""
        pygame.joystick.init()
        result = []
        for i in range(pygame.joystick.get_count()):
            js = pygame.joystick.Joystick(i)
            js.init()
            result.append({
                'id': i,
                'name': js.get_name(),
                'axes': js.get_numaxes(),
                'buttons': js.get_numbuttons(),
                'hats': js.get_numhats(),
            })
        return result
