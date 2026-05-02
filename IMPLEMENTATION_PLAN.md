# Fross Garage Band — Implementation Plan
> **Read this first at the start of every session.**
> This document is the single source of truth for what has been done,
> what is in progress, and what comes next.
> Update it before pushing to GitHub at the end of each session.

---

## Project Goal

Turn **YARG** (open-source Unity rhythm game) into **Fross Garage Band** — a
rebranded, Mac-native rock band game with an integrated **in-game Rhythmverse
song browser** built in Unity C#. The Python implementation is archived as
backup.

---

## Architecture

```
/Applications/YARG.app          ← The game (Unity, Mono backend)
  Contents/Resources/Data/
    Managed/
      Assembly-CSharp.dll       ← Main game code (patched by patch_fgb.command)
      FrossDownloadMenu.dll     ← NEW: Rhythmverse search UI (compiled from .cs)
      Mono.Cecil.dll            ← Cecil for DLL patching
    StreamingAssets/
      Credits.json              ← Backed up; optionally used for catalog fallback
      lang/*.json               ← Localized strings (Header.ProjectManager = "Download Music")

Rock Band Local/ (this repo)
  FrossDownloadMenu.cs          ← Unity C# source (compile → FrossDownloadMenu.dll)
  patch_fgb.command             ← Compile + patch YARG (run once after install)
  restore_yarg.command          ← Full rollback to original YARG state
  rebrand_yarg.command          ← Apply Fross Garage Band name/branding
  patch_download_music.command  ← Lightweight Credits.json catalog (no DLL patch)
  Launch YARG.command           ← Shortcut to open the game
  backup/python_rb_local/       ← Archived Python implementation
```

---

## Phase Status

### ✅ Phase 1 — Python prototype (archived)
Complete Python/Pygame rhythm game: guitar/drums/vocals, chart parser,
audio engine, Rhythmverse client, full UI. Archived to `backup/python_rb_local/`.

### ✅ Phase 2 — YARG as primary game
- YARG v0.14.0 installed at `/Applications/YARG.app`
- Rebranded to "Fross Garage Band" via Info.plist + lang JSONs
- Logo injected, launcher created
- `restore_yarg.command` created for safe rollback

### ✅ Phase 3 — FrossDownloadMenu (in-game Rhythmverse search)
- **`FrossDownloadMenu.cs`** written: full Unity C# MonoBehaviour that
  programmatically builds a Canvas overlay with:
  - Search bar + format filter buttons (All / CH / YARG / RB3 / PS / WTDE)
  - Scrollable song list with difficulty chips
  - Detail panel (title, artist, album, diffs, download count)
  - Download button + real-time progress bar
  - Back button
  - UnityWebRequest coroutines hitting Rhythmverse API
  - ZIP extraction to `~/Library/Application Support/YARG/songs/`
- **`patch_fgb.command`** written:
  1. Compiles `FrossDownloadMenu.cs` → `FrossDownloadMenu.dll` via `dotnet` SDK
  2. Copies DLL to YARG's `Managed/` folder
  3. Uses Mono.Cecil to patch `MainMenu.Credits()` → `FrossDownloadMenu.Show()`
  4. Re-signs `Assembly-CSharp.dll`

### 🔲 Phase 4 — Test & iterate (NEXT)
| Task | Priority | Notes |
|------|----------|-------|
| Run `patch_fgb.command` and verify compilation | HIGH | Need dotnet SDK |
| Test in-game: Menu → Download Music opens overlay | HIGH | |
| Test Rhythmverse API calls from within YARG | HIGH | CORS / UnityWebRequest |
| Test ZIP download + extraction to songs/ | HIGH | |
| Fix any runtime errors from in-game overlay | HIGH | |
| Add pagination arrows to song list | MEDIUM | Already designed |
| Add "Open in Browser" fallback button | MEDIUM | For unsupported formats (.7z) |
| Add keyboard navigation (↑↓ in list) | MEDIUM | |
| Test with PS5 controller (no mouse) | MEDIUM | |

### 🔲 Phase 5 — Polish
| Task | Priority | Notes |
|------|----------|-------|
| Use YARG's actual TMPro fonts instead of Arial | LOW | Find font assets at runtime |
| Add album art thumbnails from Rhythmverse | LOW | |
| Add "Recently downloaded" section | LOW | |
| Make overlay draggable / resizable | LOW | |
| Localize all strings via lang JSONs | LOW | |

---

## How to Run `patch_fgb.command`

Prerequisites:
```bash
brew install dotnet        # .NET SDK
```

Then double-click `patch_fgb.command` in Finder (or `bash patch_fgb.command`).

What it does:
1. Creates a temp `net472` project referencing YARG's UnityEngine DLLs
2. Compiles `FrossDownloadMenu.cs` → `FrossDownloadMenu.dll`
3. Copies the DLL to `/Applications/YARG.app/.../Managed/`
4. Builds and runs `Patcher.exe` (Mono.Cecil) that rewrites `MainMenu.Credits()`
5. Re-signs the patched assembly with `codesign`

To revert everything: `bash restore_yarg.command`

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `FrossDownloadMenu.cs` | Unity C# — compile → DLL → inject into YARG |
| `patch_fgb.command` | One-click: compile + patch YARG |
| `restore_yarg.command` | One-click: revert all patches |
| `rebrand_yarg.command` | Apply Fross Garage Band name |
| `patch_download_music.command` | Fallback: Credits.json catalog (no DLL) |
| `Launch YARG.command` | Open Fross Garage Band |
| `backup/python_rb_local/` | Archived Python game |

---

## Rhythmverse API (for C# reference)

```
POST https://rhythmverse.co/api/{gameformat}/songfiles/list
  data_type=full, page, records, sort[0][sort_by]=update_date, sort[0][sort_order]=DESC

POST https://rhythmverse.co/api/{gameformat}/songfiles/search/live
  data_type=full, text, page, records

Headers: X-Requested-With: XMLHttpRequest
         Referer: https://rhythmverse.co/songfiles/game
         Origin:  https://rhythmverse.co

Response: { status, data: { songs: [ { file: { file_id, file_title, file_artist,
            diff_guitar, diff_bass, diff_drums, diff_vocals, diff_keys,
            download_url, gameformat, completeness, downloads } } ],
            records: { total_filtered }, pagination: { records } } }

gameformat values: all  chm  yarg  rb3  rb3xbox  wtde  tbrb  ps
```

---

## Session Notes

### 2026-05-02
- Pivoted from Python game to YARG as primary game (user decision)
- Archived Python code to `backup/python_rb_local/`
- Wrote `FrossDownloadMenu.cs` (~550 lines, full Unity UI + API)
- Wrote `patch_fgb.command` (compile + Cecil patch)
- Updated README to v2.0.0
- **Next session**: Run `patch_fgb.command`, test in-game, fix runtime issues

---

## Token Budget Strategy

Each session should:
1. **Start**: Read `IMPLEMENTATION_PLAN.md` → know exact state
2. **Work**: Focus on the highest-priority NEXT task
3. **End**: Update Phase Status in this file, update README version, push to GitHub

Never re-read large files unless the task requires editing them.
Prefer targeted `Grep` over re-reading whole files.
