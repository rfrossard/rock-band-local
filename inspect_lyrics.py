from pathlib import Path
from mido import MidiFile

midi_path = Path("songs/Roxette - Almost Unreal/notes.mid")

print("MIDI:", midi_path)
if not midi_path.exists():
    print("ERRO: notes.mid não encontrado nesse caminho.")
    raise SystemExit(1)

mid = MidiFile(midi_path)
print(f"Ticks per beat: {mid.ticks_per_beat}")
print(f"Total tracks: {len(mid.tracks)}")
print()

total_lyric_events = 0

for i, track in enumerate(mid.tracks):
    lyric_count = 0
    text_count = 0
    has_vocal_hint = False

    for msg in track:
        if msg.type in ("lyrics", "lyric"):
            lyric_count += 1
        elif msg.type == "text":
            text_count += 1
            txt = (getattr(msg, "text", "") or "").lower()
            if any(hint in txt for hint in ["vocal", "lyrics", "vox"]):
                has_vocal_hint = True

    total_lyric_events += lyric_count
    print(f"Track {i}: name={track.name!r}, lyrics={lyric_count}, text={text_count}, vocal_hint={has_vocal_hint}")

print()
print("TOTAL lyric events in file:", total_lyric_events)
