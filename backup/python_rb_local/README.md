# Python Rock Band Local — Archive

This folder contains the original Python/Pygame implementation of Rock Band Local.

**Status:** Archived. YARG (Fross Garage Band) is now the primary game.

## What this was

A full Pygame rhythm game with:
- Guitar / Bass / Drums / Vocals gameplay
- Rhythmverse song browser and downloader
- Rock Band PS5 controller support
- Calibration screen, results screen, etc.

## Why archived

The project pivoted to using YARG (Unity) as the game engine, rebranded as
**Fross Garage Band**, with the Python implementation replaced by a native
Unity C# module (`FrossDownloadMenu`) for Rhythmverse integration.

## Running (if needed)

```bash
cd backup/python_rb_local
pip install -r requirements.txt
python main.py
```
