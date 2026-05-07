# 🎸 Fross Garage Band

> **YARG rebranded and extended** — a local rock band game for macOS with an
> integrated Rhythmverse song browser built natively in Unity C#.

![Unity](https://img.shields.io/badge/Unity-2022-blue?logo=unity)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/Version-2.1.0-brightgreen)

---

## What Is This?

**Fross Garage Band** takes [YARG](https://github.com/YARC-Official/YARG)
(Yet Another Rhythm Game — open source, Unity-based) and extends it with a
native in-game **Rhythmverse song downloader**, so you can find, preview, and
install songs without ever leaving the game.

The original YARG experience (gameplay, library, scoring, multiplayer) is
100% intact. The only addition is a new "Download Music" screen.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎸 Full YARG gameplay | Guitar, Bass, Drums, Vocals, Keys — all difficulties |
| 👥 Multiplayer | Local up to 4 players |
| 🎮 Controllers | PS5 Rock Band guitar & drums, keyboard, any HID |
| 📥 Download Music | In-game Rhythmverse search — find & install songs without leaving YARG |
| 🔍 Search & filter | By title, artist, or format (CH / YARG / RB3 / PS / WTDE) |
| ⬇️ Auto-install | ZIP downloaded and extracted to YARG songs folder automatically |
| 🎨 Native Unity UI | Overlay matches YARG's dark color palette, no external app |

---

## 🚀 Quick Start

### 1. Install YARG

Download the latest YARG installer from
[YARC Launcher](https://github.com/YARC-Official/YARC-Launcher/releases)
or use the `YARC.Launcher_universal.app.tar.gz` included in this repo.

### 2. Clone this repo

```bash
git clone https://github.com/rfrossard/rock-band-local.git
cd rock-band-local
```

### 3. Install the Download Music patch

Requirement (one-time):
```bash
brew install dotnet
```

Double-click **`patch_fgb.command`** in Finder, or run:
```bash
bash patch_fgb.command
```

This compiles the Unity C# extension and hooks it into YARG's main menu.

### 4. Play

Double-click **`Launch YARG.command`** — or open YARG from `/Applications`.

In the main menu, click **Download Music** to open the Rhythmverse browser.

---

## 📥 Using Download Music

1. Open Fross Garage Band
2. Click **Download Music** in the main menu
3. Search by artist or song title
4. Filter by format: `All / CH / YARG / RB3 / PS / WTDE`
5. Select a song — details appear on the right
6. Click **⬇ Baixar Música** — progress bar shows download status
7. Song is automatically extracted to `~/Library/Application Support/YARG/songs/`
8. Return to the song library — new song appears immediately

---

## 🔧 Scripts Reference

| Script | Purpose |
|---|---|
| `patch_fgb.command` | Compile + inject FrossDownloadMenu into YARG (**run once**) |
| `restore_yarg.command` | Revert all patches — restore original YARG state |
| `rebrand_yarg.command` | Apply "Fross Garage Band" name to YARG's UI strings |
| `patch_download_music.command` | Lightweight fallback: Credits.json catalog (no DLL patch) |
| `Launch YARG.command` | Open the game |

---

## 🏗️ Architecture

```
FrossDownloadMenu.cs      ← Unity C# source (edit this to change the search UI)
patch_fgb.command         ← Compiles .cs → .dll, Cecil-patches MainMenu.Credits()
restore_yarg.command      ← Rollback: restores Assembly-CSharp.dll from backup

/Applications/YARG.app/Contents/Resources/Data/
  Managed/
    Assembly-CSharp.dll     ← Patched: Credits() → FrossDownloadMenu.Show()
    FrossDownloadMenu.dll   ← NEW: the in-game search overlay
  StreamingAssets/
    lang/*.json             ← "ProjectManager" header = "📥 Download Music"
```

The patch is additive — `FrossDownloadMenu.dll` is a new assembly, and only
one call site in `Assembly-CSharp.dll` is modified. Everything else in YARG
remains untouched.

---

## ↩️ Reverting

To restore YARG to its original unpatched state:

```bash
bash restore_yarg.command
```

---

## 📁 Folder Structure

```
rock-band-local/
├── FrossDownloadMenu.cs          # Unity C# — Rhythmverse search screen
├── patch_fgb.command             # Compile + patch (main install script)
├── restore_yarg.command          # Rollback
├── rebrand_yarg.command          # Rename YARG → Fross Garage Band
├── patch_download_music.command  # Lightweight Credits.json fallback
├── Launch YARG.command           # Open the game
├── logos/                        # Logo assets + inject script
├── songs/                        # Local song library (auto-added to YARG)
├── IMPLEMENTATION_PLAN.md        # Development roadmap & session notes
└── backup/
    └── python_rb_local/          # Archived Python/Pygame prototype
```

---

## 🧑‍💻 Development

To modify the in-game search screen, edit **`FrossDownloadMenu.cs`** and
re-run `patch_fgb.command`. The script always recompiles from source.

The C# file is self-contained — no Unity Editor needed. It references YARG's
own DLLs from `Managed/` at compile time.

---

## 📋 Roadmap

See **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** for the full
phase-by-phase plan, session notes, and next steps.

**Current phase**: Phase 4 — Test & iterate  
**Next**: Run `patch_fgb.command`, test in-game, fix any runtime issues

---

## 🙏 Credits

- [YARG](https://github.com/YARC-Official/YARG) — the open-source rhythm game this builds on
- [Rhythmverse](https://rhythmverse.co) — song file database and download platform
- [Mono.Cecil](https://github.com/jbevain/cecil) — .NET assembly manipulation

---

## Changelog

### v2.1.0 — 2026-05-02
- **Fixed**: `restore_yarg.command` now restores `.bak_fgb` → audio regression after patch is recoverable
- **Fixed**: `FrossDownloadMenu.cs` complete layout rewrite — was using wrong RectTransform anchor math causing black screen; new `Band()`/`BandBottom()`/`Stretch()` helpers produce correct layout
- **New**: `SKILL.md` — Unity/Cecil/API reference for future sessions

### v2.0.0 — 2026-05-02
- **New**: `FrossDownloadMenu.cs` — full in-game Rhythmverse search overlay (Unity C#)
- **New**: `patch_fgb.command` — one-click compile + Cecil patch workflow
- **New**: `IMPLEMENTATION_PLAN.md` — session continuity document
- **Changed**: YARG is now the primary game; Python implementation archived to `backup/`
- **Changed**: README rewritten to reflect Unity-first architecture

### v1.5.0 — 2026-04-28
- `restore_yarg.command` with DLL backup + lang JSON validation
- `patch_download_music.command` — Credits.json catalog (no DLL)
- Audio preview in Python SongSelectScreen

### v1.0.0 — 2026-04-20
- Initial release: full Python/Pygame rhythm game + Rhythmverse integration
- YARG rebranding (Fross Garage Band), logo injection
