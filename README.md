# 🎸 Rock Band Local

> Local Rock Band game for macOS — combining the best of **YARG**, **Clone Hero**, **Frets on Fire** and **Guitar Hero World Tour Definitive Edition**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame-2.5%2B-green)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎸 Guitar / Bass | 5 frets, strum, sustains, HOPOs |
| 🥁 Drums | 5 pads (kick + 4 pads), cymbal support |
| 🎤 Vocals | Real-time pitch detection via USB mic |
| ⭐ Star Power | Overdrive with 2× multiplier (tilt/button) |
| 👥 Multiplayer | Up to 4 simultaneous players |
| 🌐 Rhythmverse | Browse & download songs in-game |
| 🎛️ Calibration | Interactive latency offset calibration |
| 📊 Results | SSS→F grades, 0–6 stars, full combo, accuracy |

---

## 🎮 Supported Controllers

| Device | Connection | Status |
|---|---|---|
| Guitar Rock Band PS5 (PDP Riffmaster) | Bluetooth | ✅ Auto-detected |
| Drums Rock Band PS5 | USB | ✅ Auto-detected |
| USB Microphone | USB | ✅ Auto-detected |
| Keyboard | — | ✅ Always available |

### Keyboard Controls

**Guitar (Player 1)**
```
Frets:      S  D  F  J  K   (green, red, yellow, blue, orange)
Strum:      ↑  ↓
Star Power: SPACE
```

**Drums (Player 1)**
```
Pads: V (kick)  F (red)  G (yellow)  H (blue)  J (green)
```

---

## 🚀 Installation

### macOS / Linux (recommended)
```bash
git clone https://github.com/rfrossard/rock-band-local.git
cd rock-band-local
chmod +x install.sh
./install.sh
source .venv/bin/activate
python main.py
```

### Manual install
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

> **Note:** `sounddevice` and `aubio` are optional — only needed for vocal pitch detection.

---

## 🎵 Adding Songs

### Local songs
Drop any folder containing a `notes.chart` (or `notes.mid`) into `songs/`. The game auto-discovers on startup.

```
songs/
└── Song Name - Artist/
    ├── notes.chart        ← required
    ├── song.ogg           ← main audio / backing track
    ├── guitar.ogg         ← guitar stem (optional)
    ├── bass.ogg           ← bass stem (optional)
    ├── drums.ogg          ← drums stem (optional)
    └── vocals.ogg         ← vocals stem (optional)
```

**Recommended chart sources:**
- [Chorus.fightthe.pw](https://chorus.fightthe.pw) — historic archive
- [Rhythmverse.co](https://rhythmverse.co) — directly from the in-game menu

### Via Rhythmverse (in-game)
Main Menu → **🌐 Browse Rhythmverse** → search → ⬇️ Download

---

## ⚙️ Configuration

Edit `config.json` or use the **⚙️ Settings** menu in-game:

```json
{
  "audio": {
    "latency_offset_ms": 0,
    "master_volume": 0.8
  },
  "video": {
    "fullscreen": false,
    "note_speed": 5
  },
  "players": [
    { "instrument": "guitar", "difficulty": "medium" },
    { "instrument": "drums",  "difficulty": "medium" }
  ]
}
```

---

## 🗺️ Project Structure

```
rock-band-local/
├── main.py                      ← entry point
├── config.json                  ← game settings
├── requirements.txt
├── install.sh / run.sh
│
├── game/
│   ├── constants.py             ← colors, states, enums
│   ├── chart_parser.py          ← .chart and .mid parser
│   ├── audio_engine.py          ← stem playback + sync
│   ├── input_handler.py         ← keyboard + joystick + mic
│   ├── note_engine.py           ← highway, hit detection
│   └── scoring.py               ← score, multiplier, Star Power
│
├── ui/
│   ├── base_screen.py
│   ├── main_menu.py
│   ├── song_select.py
│   ├── gameplay_screen.py       ← 3D note highway (YARG-style)
│   ├── results_screen.py
│   ├── calibration_screen.py
│   ├── rhythmverse_screen.py    ← Rhythmverse browser
│   └── settings_screen.py
│
├── network/
│   └── rhythmverse_client.py    ← HTTP client + download
│
├── logos/                       ← custom YARG branding
│   ├── inject_logo.py           ← injects PNGs into YARG assets
│   ├── Run Injector.command     ← double-click launcher (macOS)
│   ├── Logo_White.png           ← 1024×512
│   ├── Splash_Logo.png          ← 1920×1080
│   ├── Header.png               ← 1920×300
│   ├── PauseBackground.png      ← 1920×1080
│   └── YARG_Colorless.png       ← 512×512
│
└── design/                      ← UI design systems
    ├── fross-design-system.html ← YARG-inspired web UI reference
    └── minecraft-design-system.html
```

---

## 🎨 Custom Branding (YARG Logo Injector)

The `logos/` folder contains the **Fross Garage Band** branding and a script to inject custom logos into YARG's Unity assets.

```bash
# Requires .venv with UnityPy + Pillow (already set up by install.sh)
python3 logos/inject_logo.py

# Or double-click "Run Injector.command" in Finder
```

> Replace any PNG in `logos/` keeping the exact pixel dimensions, then re-run. YARG must be closed.

---

## 🏆 Scoring System

| Accuracy | Window | Points |
|---|---|---|
| Perfect | ±20 ms | 50 × multiplier |
| Good | ±45 ms | 50 × multiplier |
| OK | ±70 ms | 50 × multiplier |
| Miss | > 70 ms | 0 |

**Multiplier:** increases by 1× every 10 consecutive notes (max ×4). Star Power doubles it.

**Grades:** SSS (100%) › SS (≥95%) › S (≥90%) › A (≥80%) › B (≥70%) › C › D › F

---

## ⌨️ Global Shortcuts

| Key | Action |
|---|---|
| `F11` | Toggle fullscreen |
| `P` | Pause / resume |
| `ESC` | Back / quit |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `pygame` | Game engine, rendering, input |
| `requests` + `beautifulsoup4` | Rhythmverse integration |
| `Pillow` | Logo generation & injection |
| `numpy` | Audio processing |
| `sounddevice` *(optional)* | USB microphone input |
| `aubio` *(optional)* | Real-time pitch detection (vocals) |
| `UnityPy` *(logos only)* | YARG asset injection |

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add some feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

> **Disclaimer:** This project is a fan-made tool. YARG, Clone Hero, Rock Band, and Guitar Hero are trademarks of their respective owners. Song charts require proper licensing — this repo does not include any copyrighted music.
