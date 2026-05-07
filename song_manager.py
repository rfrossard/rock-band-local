#!/usr/bin/env python3
"""
Fross Song Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Busca músicas no Rhythmverse, baixa, converte RB3CON → YARG
e testa a compatibilidade — tudo em um clique.

Uso:  python3 song_manager.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Callable, Dict, List, Optional

# ── Project paths ─────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

SONGS_DIR = PROJECT_DIR / "songs"
ONYX_CLI  = PROJECT_DIR / "onyx-cli"
SONGS_DIR.mkdir(exist_ok=True)

# ── Network client ────────────────────────────────────────────────────────────
from network.rhythmverse_client import RhythmverseClient, RVSong, SearchResult, GAMEFORMATS  # noqa

import tkinter as tk
from tkinter import ttk

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#14142A"
CARD    = "#1C1C34"
SEL     = "#26264A"
ACCENT  = "#4A8ED0"
SUCCESS = "#46C06C"
WARN    = "#E09428"
ERR     = "#E04848"
TEXT    = "#DDDDF2"
DIM     = "#72729A"
BORDER  = "#2C2C52"

FMT_CLR: Dict[str, str] = {
    "chm":     "#3CA04E",
    "yarg":    "#4A8ED0",
    "rb3":     "#C83C3C",
    "rb3xbox": "#C83C3C",
    "rb3wii":  "#C84C3C",
    "rb3ps3":  "#C83C4C",
    "tbrb":    "#9038C4",
    "ps":      "#3CA0B4",
    "wtde":    "#B04C18",
}

# Formatos YARG sem conversão (CH = Clone Hero também funciona)
YARG_NATIVE = {"chm", "yarg", "ps", "ch"}
# Formatos que precisam do Onyx
NEEDS_ONYX  = {"rb3", "rb3xbox", "rb3wii", "rb3ps3", "tbrb"}


# ══════════════════════════════════════════════════════════════════════════════
# Conversion Engine
# ══════════════════════════════════════════════════════════════════════════════

class CompatResult:
    """Resultado da verificação de compatibilidade de uma pasta de música."""

    def __init__(self) -> None:
        self.exists    = False
        self.folder:   Optional[Path] = None
        self.has_audio = False
        self.has_chart = False
        self.has_ini   = False
        self.audio_ok  = False
        self.audio_info: Optional[dict] = None
        self.issues:   List[str] = []

    @property
    def compatible(self) -> bool:
        return self.exists and self.has_audio and self.audio_ok and self.has_chart

    @property
    def fixable(self) -> bool:
        """Pode ser corrigido apenas com ffmpeg (áudio errado mas chart OK)."""
        return self.exists and self.has_audio and not self.audio_ok and self.has_chart

    def summary(self) -> str:
        if self.compatible:
            return "✅  Compatível com YARG"
        parts = []
        if not self.has_audio:
            parts.append("sem áudio")
        elif not self.audio_ok:
            info = self.audio_info or {}
            parts.append(f"áudio {info.get('sample_rate',0)//1000}kHz → precisa 44 100 Hz")
        if not self.has_chart:
            parts.append("sem chart")
        return "⚠️  " + " · ".join(parts) if parts else "⚠️  problemas desconhecidos"


class SongConverter:
    """Gerencia detecção, conversão e verificação de músicas para o YARG."""

    AUDIO_EXTS  = {".ogg", ".opus"}
    CHART_NAMES = {"notes.mid", "notes.chart", "song.chart"}

    def __init__(self) -> None:
        self.songs_dir = SONGS_DIR
        self.onyx_cli  = ONYX_CLI

    # ── Busca no disco ────────────────────────────────────────────────────────

    def find_existing(self, song: RVSong) -> Optional[Path]:
        """Retorna a pasta se a música já existe em songs/ (matching aproximado)."""
        candidates = [
            f"{song.artist} - {song.title}",
            song.title,
            re.sub(r"[:/]", " ", f"{song.artist} - {song.title}"),
        ]
        for name in candidates:
            p = self.songs_dir / self._safe(name)
            if p.is_dir():
                return p

        # Fuzzy: pasta que contenha o título
        t = song.title.lower()
        for item in self.songs_dir.iterdir():
            if item.is_dir() and t in item.name.lower():
                return item
        return None

    # ── Verificação de compatibilidade ────────────────────────────────────────

    def check_compat(self, folder: Path) -> CompatResult:
        r = CompatResult()
        r.exists = folder.is_dir()
        r.folder = folder
        if not r.exists:
            r.issues.append("Pasta não encontrada")
            return r

        files = {f.name.lower(): f for f in folder.iterdir() if f.is_file()}

        # Áudio
        ogg = folder / "song.ogg"
        mogg = folder / "song.mogg"
        if ogg.exists():
            r.has_audio = True
            info = self._ffprobe(ogg)
            r.audio_info = info
            if info:
                ok = info["sample_rate"] == 44100 and info["channels"] <= 2
                r.audio_ok = ok
                if not ok:
                    r.issues.append(
                        f"Áudio: {info['sample_rate']} Hz {info['channels']}ch"
                        f" → precisa 44 100 Hz stereo"
                    )
            else:
                r.issues.append("Não foi possível ler o áudio (ffprobe ausente?)")
        elif mogg.exists():
            r.has_audio = True
            r.issues.append("Áudio em MOGG — precisa unwrap com Onyx")
        else:
            r.issues.append("Sem arquivo de áudio (song.ogg)")

        # Chart
        chart_found = any(n in files for n in self.CHART_NAMES)
        r.has_chart = chart_found
        if not chart_found:
            r.issues.append("Sem chart (notes.mid / notes.chart)")

        # INI (opcional mas recomendado)
        r.has_ini = "song.ini" in files

        return r

    def _ffprobe(self, path: Path) -> Optional[dict]:
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", str(path)],
                capture_output=True, text=True, timeout=10,
            )
            for s in json.loads(out.stdout).get("streams", []):
                if s.get("codec_type") == "audio":
                    return {
                        "sample_rate": int(s.get("sample_rate", 0)),
                        "channels":    int(s.get("channels", 0)),
                        "codec":       s.get("codec_name", ""),
                    }
        except Exception:
            pass
        return None

    # ── Pipeline principal ────────────────────────────────────────────────────

    def process_folder(
        self,
        song:    RVSong,
        folder:  Path,
        log:     Callable[[str], None],
    ) -> Optional[Path]:
        """
        Recebe a pasta já baixada (extraída pelo RhythmverseClient),
        detecta o formato e converte / corrige para o YARG.
        Retorna a pasta final em songs/ ou None em caso de falha.
        """
        fmt = song.gameformat.lower()

        if fmt in NEEDS_ONYX:
            log(f"🔄  Formato {fmt.upper()} — convertendo com Onyx...")
            return self._pipeline_rb3(song, folder, log)
        else:
            log(f"🎵  Formato {fmt.upper()} — ajustando para YARG...")
            return self._pipeline_native(song, folder, log)

    # ── Pipeline RB3 (Onyx + ffmpeg) ─────────────────────────────────────────

    def _pipeline_rb3(
        self,
        song:   RVSong,
        src:    Path,
        log:    Callable,
    ) -> Optional[Path]:
        work = PROJECT_DIR / f"_tmp_{int(time.time())}"
        work.mkdir(exist_ok=True)

        safe_name = self._safe(f"{song.artist} - {song.title}")
        final     = self.songs_dir / safe_name

        try:
            # 1) Encontrar o arquivo rb3con (binário grande sem extensão)
            rb3con = self._find_rb3con(src)

            if rb3con:
                log(f"📦  {rb3con.name}")
                ok = self._onyx_convert(rb3con, work, log)
                if not ok:
                    ok = self._onyx_extract(rb3con, work, log)
                if not ok:
                    log("❌  Onyx não conseguiu processar o arquivo")
                    return None
            else:
                # Talvez os arquivos já estejam soltos dentro de src
                for item in src.rglob("*"):
                    if item.is_file():
                        dst = work / item.name
                        shutil.copy2(item, dst)

            # 2) Desencriptar MOGGs encontrados
            moggs = list(work.rglob("*.mogg"))
            ogg_path: Optional[Path] = None

            if moggs:
                log("🔓  Desencriptando MOGG...")
                raw = work / "song_raw.ogg"
                r = subprocess.run(
                    [str(self.onyx_cli), "unwrap", str(moggs[0]), "--to", str(raw)],
                    capture_output=True, text=True, timeout=90,
                )
                if r.returncode == 0 and raw.exists():
                    ogg_path = raw
                else:
                    log(f"⚠️   Onyx unwrap falhou — tentando ffmpeg direto no MOGG")
                    ogg_path = moggs[0]
            else:
                candidates = [
                    f for f in work.rglob("*.ogg")
                    if "backup" not in f.name and "raw" not in f.name
                ]
                if candidates:
                    ogg_path = candidates[0]

            # 3) Reencodar → 44 100 Hz stereo
            final_ogg: Optional[Path] = None
            if ogg_path and ogg_path.exists():
                log("🎵  Reencodando → 44 100 Hz stereo...")
                final_ogg = work / "song_out.ogg"
                r = subprocess.run(
                    ["ffmpeg", "-y", "-i", str(ogg_path),
                     "-ar", "44100", "-ac", "2", str(final_ogg)],
                    capture_output=True, text=True, timeout=300,
                )
                if r.returncode != 0:
                    log(f"❌  ffmpeg: {r.stderr[-200:]}")
                    return None
                log("✅  Áudio OK")
            else:
                log("⚠️   Nenhum áudio encontrado após extração")

            # 4) Coletar chart / ini
            mids    = list(work.rglob("*.mid"))
            charts  = list(work.rglob("*.chart"))
            ini_src = next(iter(work.rglob("song.ini")), None)

            # 5) Montar pasta final
            self._backup_if_exists(final, log)
            final.mkdir(parents=True, exist_ok=True)

            if final_ogg and final_ogg.exists():
                shutil.copy2(final_ogg, final / "song.ogg")

            if mids:
                shutil.copy2(mids[0], final / "notes.mid")
                log("✅  Chart (MIDI) copiado")
            elif charts:
                shutil.copy2(charts[0], final / "notes.chart")
                log("✅  Chart (.chart) copiado")
            else:
                log("⚠️   Chart não encontrado — a música ficará sem notas no YARG")

            if ini_src:
                shutil.copy2(ini_src, final / "song.ini")
            else:
                (final / "song.ini").write_text(
                    f"[song]\nname = {song.title}\nartist = {song.artist}\n"
                    f"album = {song.album}\nyear = {song.year}\n"
                    f"charter = {song.charter or 'RB3 Import'}\n",
                    encoding="utf-8",
                )
            log("✅  Metadados OK")

            return final

        except Exception as e:
            log(f"❌  Erro inesperado: {e}")
            return None
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _find_rb3con(self, folder: Path) -> Optional[Path]:
        """Procura o arquivo RB3CON: binário grande sem extensão ou com _rb3con no nome."""
        for f in sorted(folder.rglob("*"), key=lambda p: -p.stat().st_size if p.is_file() else 0):
            if not f.is_file() or f.name.startswith("."):
                continue
            name = f.name.lower()
            if "_rb3con" in name or f.suffix == "":
                if f.stat().st_size > 500_000:  # arquivos > 500 KB
                    return f
        return None

    def _onyx_convert(self, src: Path, out: Path, log: Callable) -> bool:
        r = subprocess.run(
            [str(self.onyx_cli), "song", "convert",
             "--input", str(src), "--output", str(out), "--format", "clonehero"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            log(f"⚠️   Onyx convert: {r.stderr[:150]}")
        return r.returncode == 0

    def _onyx_extract(self, src: Path, out: Path, log: Callable) -> bool:
        r = subprocess.run(
            [str(self.onyx_cli), "extract", str(src), "--to", str(out)],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode != 0:
            log(f"⚠️   Onyx extract: {r.stderr[:150]}")
        return r.returncode == 0

    # ── Pipeline nativo (CH / YARG / PS) ─────────────────────────────────────

    def _pipeline_native(
        self,
        song:   RVSong,
        src:    Path,
        log:    Callable,
    ) -> Optional[Path]:
        safe_name = self._safe(f"{song.artist} - {song.title}")
        final     = self.songs_dir / safe_name

        # Se o src JÁ É a pasta final, trabalhar in-place
        if src.resolve() == final.resolve():
            return self._fix_audio_inplace(final, log)

        # Senão, copiar para a pasta final
        self._backup_if_exists(final, log)
        final.mkdir(parents=True, exist_ok=True)

        # Encontrar raiz do conteúdo dentro do src
        content_root = self._find_content_root(src)
        log(f"📂  Conteúdo: {content_root.relative_to(PROJECT_DIR)}")

        for item in content_root.iterdir():
            dst = final / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)

        return self._fix_audio_inplace(final, log)

    def _find_content_root(self, base: Path) -> Path:
        """Encontra a pasta que contém o ogg/mid/chart — pode ser base ou uma subpasta."""
        for folder in [base] + [d for d in base.rglob("*") if d.is_dir()]:
            files = {f.name.lower() for f in folder.iterdir() if f.is_file()}
            if "song.ogg" in files or "notes.mid" in files or "notes.chart" in files:
                return folder
        return base

    def _fix_audio_inplace(self, folder: Path, log: Callable) -> Optional[Path]:
        """Verifica e corrige o áudio (44 100 Hz stereo) se necessário."""
        ogg  = folder / "song.ogg"
        mogg = folder / "song.mogg"

        # MOGG sem OGG → precisa unwrap primeiro
        if mogg.exists() and not ogg.exists():
            log("🔓  Desencriptando MOGG...")
            raw = folder / "song_raw.ogg"
            r = subprocess.run(
                [str(self.onyx_cli), "unwrap", str(mogg), "--to", str(raw)],
                capture_output=True, text=True, timeout=90,
            )
            if r.returncode == 0 and raw.exists():
                ogg = raw
            else:
                log("❌  Onyx unwrap falhou no MOGG")
                return None

        if not ogg.exists():
            log("⚠️   Sem song.ogg — música pode não tocar no YARG")
            return folder

        info = self._ffprobe(ogg)
        if info and info["sample_rate"] == 44100 and info["channels"] <= 2:
            log("✅  Áudio já compatível (44 100 Hz stereo)")
            return folder

        sr = info["sample_rate"] if info else "?"
        log(f"🎵  Corrigindo áudio ({sr} Hz → 44 100 Hz stereo)...")

        bak = folder / "song_backup.ogg"
        # Se o ogg é o mesmo arquivo de saída, faz backup
        out_ogg = folder / "song.ogg"
        if ogg != out_ogg:
            shutil.copy2(ogg, bak)
            ffmpeg_input = ogg
        else:
            shutil.copy2(ogg, bak)
            ffmpeg_input = bak

        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(ffmpeg_input),
             "-ar", "44100", "-ac", "2", str(out_ogg)],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0:
            log("✅  Áudio corrigido!")
            return folder
        else:
            # Rollback
            shutil.copy2(bak, out_ogg)
            log(f"❌  ffmpeg falhou: {r.stderr[-100:]}")
            return None

    # ── Utilitários ───────────────────────────────────────────────────────────

    def _backup_if_exists(self, path: Path, log: Callable) -> None:
        if path.exists():
            bak = path.parent / f"{path.name}__bak_{int(time.time())}"
            shutil.move(str(path), str(bak))
            log(f"📂  Backup: {bak.name}")

    @staticmethod
    def _safe(name: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ")
        return safe[:120] or "song"


# ══════════════════════════════════════════════════════════════════════════════
# UI — Fross Song Manager
# ══════════════════════════════════════════════════════════════════════════════

FILTER_FORMATS = [
    ("Todos", "all"), ("CH", "chm"), ("YARG", "yarg"),
    ("RB3",   "rb3"), ("PS",  "ps"), ("WTDE", "wtde"),
]

DIFF_STARS = lambda d: "★" * min(d, 6) + "☆" * (6 - min(d, 6)) if d >= 0 else ""


class App(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("🎸  Fross Song Manager")
        self.geometry("1160x720")
        self.minsize(900, 580)
        self.configure(bg=BG)

        # Data
        cfg = {"rhythmverse": {
            "base_url":      "https://rhythmverse.co",
            "download_path": str(SONGS_DIR),
            "cache_ttl_seconds": 300,
        }}
        self._client     = RhythmverseClient(cfg, download_dir=str(SONGS_DIR))
        self._conv       = SongConverter()
        self._songs:     List[RVSong] = []
        self._selected:  Optional[RVSong] = None
        self._page       = 1
        self._total_pages = 1
        self._total_songs = 0
        self._gameformat = "all"
        self._loading    = False
        self._processing = False

        self._style_setup()
        self._ui_build()
        self._do_search()

    # ── Style ─────────────────────────────────────────────────────────────────

    def _style_setup(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".",                background=BG,   foreground=TEXT, borderwidth=0)
        s.configure("TFrame",           background=BG)
        s.configure("TLabel",           background=BG,   foreground=TEXT)
        s.configure("TScrollbar",       background=CARD, troughcolor=BG,
                    arrowcolor=DIM, bordercolor=BG)
        s.configure("Prog.Horizontal.TProgressbar",
                    background=ACCENT, troughcolor=CARD,
                    bordercolor=CARD, lightcolor=ACCENT, darkcolor=ACCENT)

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _ui_build(self) -> None:
        self._build_topbar()
        self._build_main()
        self._build_statusbar()

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = tk.Frame(self, bg=CARD, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # App name
        tk.Label(bar, text="🎸  Fross Song Manager",
                 bg=CARD, fg=TEXT, font=("", 15, "bold"),
                 padx=18).pack(side="left", pady=12)

        # Format filter chips
        chip_frame = tk.Frame(bar, bg=CARD)
        chip_frame.pack(side="right", padx=14)
        self._fmt_btns: Dict[str, tk.Button] = {}
        for label, fmt in FILTER_FORMATS:
            clr = FMT_CLR.get(fmt, DIM)
            active = fmt == self._gameformat
            b = tk.Button(
                chip_frame, text=label,
                bg=clr if active else CARD,
                fg="white" if active else DIM,
                relief="flat", padx=10, pady=4,
                font=("", 10, "bold"), cursor="hand2",
                activebackground=clr, activeforeground="white",
                command=lambda f=fmt: self._set_format(f),
            )
            b.pack(side="left", padx=2)
            self._fmt_btns[fmt] = b

        # Search
        self._q_var = tk.StringVar()
        placeholder = "Buscar artista, título, charter..."
        entry_fr = tk.Frame(bar, bg=BORDER, padx=1, pady=1)
        entry_fr.pack(side="left", pady=10, ipady=0)
        self._search_entry = tk.Entry(
            entry_fr, textvariable=self._q_var,
            bg=CARD, fg=DIM, insertbackground=TEXT,
            relief="flat", font=("", 12), width=30, bd=6,
        )
        self._search_entry.insert(0, placeholder)
        self._search_entry.pack()
        self._search_entry.bind("<FocusIn>",  lambda e: self._ph_in(placeholder))
        self._search_entry.bind("<FocusOut>", lambda e: self._ph_out(placeholder))
        self._search_entry.bind("<Return>",   lambda e: self._trigger_search())

        tk.Button(
            bar, text="Buscar", bg=ACCENT, fg="white", relief="flat",
            font=("", 11, "bold"), padx=16, pady=2, cursor="hand2",
            activebackground="#3A7EC0", activeforeground="white",
            command=self._trigger_search,
        ).pack(side="left", padx=(6, 0), pady=15)

    # ── Main area ─────────────────────────────────────────────────────────────

    def _build_main(self) -> None:
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        # ── Left: song list ──────────────────────────────────────────────────
        list_frame = tk.Frame(main, bg=CARD)
        list_frame.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        self._lb = tk.Listbox(
            list_frame, yscrollcommand=sb.set,
            bg=CARD, fg=TEXT,
            selectbackground=SEL, selectforeground=TEXT,
            activestyle="none", relief="flat", bd=0,
            font=("", 12), highlightthickness=0,
            selectborderwidth=0,
        )
        sb.config(command=self._lb.yview)
        sb.pack(side="right", fill="y")
        self._lb.pack(fill="both", expand=True, padx=(0, 0))
        self._lb.bind("<<ListboxSelect>>", self._on_list_select)
        self._lb.bind("<Double-Button-1>", lambda e: self._do_action())
        self._lb.bind("<Return>",          lambda e: self._do_action())

        # ── Right: detail panel ───────────────────────────────────────────────
        self._detail = tk.Frame(main, bg=CARD, width=355)
        self._detail.pack(side="right", fill="y", padx=(8, 0))
        self._detail.pack_propagate(False)
        self._build_detail()

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _build_detail(self) -> None:
        d = self._detail
        for w in d.winfo_children():
            w.destroy()

        # Title + artist
        self._d_title  = tk.Label(d, text="Selecione uma música",
                                   bg=CARD, fg=TEXT, font=("", 14, "bold"),
                                   wraplength=328, justify="left", anchor="w")
        self._d_title.pack(fill="x", padx=16, pady=(16, 2))

        self._d_artist = tk.Label(d, text="",
                                   bg=CARD, fg=DIM, font=("", 11), anchor="w")
        self._d_artist.pack(fill="x", padx=16)

        self._sep(d)

        # Metadata grid
        self._meta = tk.Frame(d, bg=CARD)
        self._meta.pack(fill="x", padx=16)

        self._sep(d)

        # Instruments
        self._inst = tk.Frame(d, bg=CARD)
        self._inst.pack(fill="x", padx=16)

        self._sep(d)

        # Compat status (small)
        self._compat_var = tk.StringVar(value="")
        self._compat_lbl = tk.Label(
            d, textvariable=self._compat_var,
            bg=CARD, fg=DIM, font=("", 10),
            wraplength=328, justify="left", anchor="w",
        )
        self._compat_lbl.pack(fill="x", padx=16, pady=(4, 2))

        # Inline log (shown during processing)
        self._log = tk.Text(
            d, bg=BG, fg=DIM, font=("Menlo", 9), relief="flat",
            bd=0, height=7, wrap="word", state="disabled",
            highlightthickness=0,
        )
        # Packed on demand

        # Bottom: action buttons (anchored to bottom)
        btn_fr = tk.Frame(d, bg=CARD)
        btn_fr.pack(fill="x", padx=16, side="bottom", pady=14)

        self._web_btn = tk.Button(
            btn_fr, text="🌐  Ver no Rhythmverse",
            bg=CARD, fg=DIM, relief="flat", font=("", 10),
            pady=7, cursor="hand2",
            activebackground=SEL, activeforeground=TEXT,
            command=self._open_web, state="disabled",
        )
        self._web_btn.pack(fill="x", pady=(4, 0))

        self._action_btn = tk.Button(
            btn_fr, text="—",
            bg=CARD, fg=DIM, relief="flat", font=("", 12, "bold"),
            pady=11, cursor="hand2",
            state="disabled",
            command=self._do_action,
        )
        self._action_btn.pack(fill="x")

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=CARD, height=42)
        bar.pack(fill="x", pady=(8, 0))
        bar.pack_propagate(False)

        self._status_var = tk.StringVar(value="🌐  Conectando ao Rhythmverse...")
        tk.Label(
            bar, textvariable=self._status_var,
            bg=CARD, fg=DIM, font=("", 10), anchor="w",
        ).pack(side="left", padx=14, fill="y")

        # Pagination nav
        nav = tk.Frame(bar, bg=CARD)
        nav.pack(side="right", padx=10)
        tk.Button(nav, text="◀", bg=CARD, fg=DIM, relief="flat",
                  font=("", 12), cursor="hand2",
                  command=lambda: self._go_page(-1)).pack(side="left")
        self._page_var = tk.StringVar(value="—")
        tk.Label(nav, textvariable=self._page_var,
                 bg=CARD, fg=DIM, font=("", 10), width=9).pack(side="left")
        tk.Button(nav, text="▶", bg=CARD, fg=DIM, relief="flat",
                  font=("", 12), cursor="hand2",
                  command=lambda: self._go_page(1)).pack(side="left")

        # Progress bar (hidden until needed)
        self._prog = ttk.Progressbar(
            self, orient="horizontal", mode="determinate",
            style="Prog.Horizontal.TProgressbar",
        )

    # ── Search flow ───────────────────────────────────────────────────────────

    def _trigger_search(self) -> None:
        self._page = 1
        self._do_search()

    def _do_search(self) -> None:
        if self._loading:
            return
        q = self._get_query()
        self._loading = True
        self._status_var.set("🔄  Buscando...")
        self._lb.delete(0, "end")

        def task():
            try:
                result = self._client.search(
                    query=q, page=self._page, gameformat=self._gameformat,
                )
                self.after(0, self._show_results, result)
            except Exception as ex:
                self.after(0, self._status_var.set, f"❌  Erro de rede: {ex}")
            finally:
                self._loading = False

        threading.Thread(target=task, daemon=True).start()

    def _show_results(self, result: SearchResult) -> None:
        self._songs       = result.songs
        self._total_pages = result.total_pages
        self._total_songs = result.total_songs

        self._lb.delete(0, "end")
        for song in result.songs:
            existing = self._conv.find_existing(song)
            if existing:
                compat = self._conv.check_compat(existing)
                icon = "✅" if compat.compatible else "🔄"
            elif song.has_direct_download:
                icon = "⬇ " if song.gameformat not in NEEDS_ONYX else "🔄⬇"
            else:
                icon = "🔗"

            fmt  = f"[{song.gameformat.upper()[:5]}]"
            name = song.artist + " — " + song.title if song.artist else song.title
            self._lb.insert("end", f"  {icon}  {fmt:<7}  {name}")

        q = result.query
        if q:
            self._status_var.set(f'🔍  {result.total_songs:,} resultados para "{q}"')
        elif result.total_songs == 0:
            self._status_var.set("❌  Sem conexão ou nenhuma música encontrada")
        else:
            self._status_var.set(f"📂  {result.total_songs:,} músicas disponíveis")

        self._page_var.set(f"{self._page:,} / {self._total_pages:,}")

    def _on_list_select(self, _event=None) -> None:
        sel = self._lb.curselection()
        if not sel or sel[0] >= len(self._songs):
            return
        song = self._songs[sel[0]]
        if song is self._selected:
            return
        self._selected = song
        self._hide_log()
        self._refresh_detail(song)

    # ── Detail panel update ───────────────────────────────────────────────────

    def _refresh_detail(self, song: RVSong) -> None:
        self._d_title.config(text=song.title or "—")
        self._d_artist.config(text=song.artist or "Artista desconhecido")

        # Metadata
        for w in self._meta.winfo_children():
            w.destroy()

        def row(icon: str, val, color: str = DIM) -> None:
            if not val:
                return
            f = tk.Frame(self._meta, bg=CARD)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=icon, bg=CARD, fg=color,
                     font=("", 10), width=2).pack(side="left")
            tk.Label(f, text=str(val)[:38], bg=CARD, fg=color,
                     font=("", 10), anchor="w").pack(side="left")

        fmt = song.gameformat
        row("🎮", GAMEFORMATS.get(fmt, fmt), FMT_CLR.get(fmt, DIM))
        if song.charter:   row("✍", song.charter,           SUCCESS)
        if song.genre:     row("🎵", song.genre)
        if song.year:      row("📅", song.year)
        if song.album:     row("💿", song.album)
        if song.audio_type: row("🔊", song.audio_type)
        if song.downloads: row("⬇", f"{song.downloads:,}×")

        # Instruments
        for w in self._inst.winfo_children():
            w.destroy()
        insts = [
            ("🎸", "Guitarra", song.has_guitar, song.diff_guitar),
            ("🎵", "Baixo",    song.has_bass,   song.diff_bass),
            ("🥁", "Bateria",  song.has_drums,  song.diff_drums),
            ("🎤", "Vocal",    song.has_vocals, song.diff_vocals),
            ("🎹", "Keys",     song.has_keys,   song.diff_keys),
        ]
        for icon, name, present, diff in insts:
            if present:
                f = tk.Frame(self._inst, bg=CARD)
                f.pack(fill="x", pady=1)
                tk.Label(f, text=f"{icon} {name}", bg=CARD, fg=TEXT,
                         font=("", 10), width=12, anchor="w").pack(side="left")
                if diff >= 0:
                    tk.Label(f, text=DIFF_STARS(diff), bg=CARD, fg=WARN,
                             font=("", 9)).pack(side="left")

        # Compat + action
        self._set_action_for(song)
        self._web_btn.config(state="normal")

    def _set_action_for(self, song: RVSong) -> None:
        existing = self._conv.find_existing(song)
        fmt = song.gameformat.lower()

        if existing:
            compat = self._conv.check_compat(existing)
            if compat.compatible:
                self._compat_var.set(f"✅  Já no YARG  ({existing.name})")
                self._action_btn.config(
                    text="🔄  Re-processar (forçar atualização)",
                    bg="#1E4A2A", fg=SUCCESS, state="normal",
                )
            else:
                self._compat_var.set(compat.summary())
                self._action_btn.config(
                    text="🔧  Corrigir e preparar para YARG",
                    bg=WARN, fg="white", state="normal",
                )
        elif not song.has_direct_download:
            self._compat_var.set("🔗  Sem download direto — ver no Rhythmverse")
            self._action_btn.config(
                text="🌐  Abrir Página de Download",
                bg=DIM, fg=TEXT, state="normal",
            )
        elif fmt in NEEDS_ONYX:
            self._compat_var.set(
                f"🔄  Formato {fmt.upper()} → será convertido com Onyx"
            )
            self._action_btn.config(
                text=f"⬇  Baixar e Converter para YARG",
                bg=ACCENT, fg="white", state="normal",
            )
        else:
            self._compat_var.set(
                f"✅  Formato {fmt.upper()} compatível com YARG"
            )
            self._action_btn.config(
                text=f"⬇  Baixar para YARG",
                bg=ACCENT, fg="white", state="normal",
            )

    # ── Action button ─────────────────────────────────────────────────────────

    def _do_action(self) -> None:
        if self._processing or self._selected is None:
            return
        song = self._selected

        if not song.has_direct_download:
            self._open_web()
            return

        self._processing = True
        self._action_btn.config(state="disabled", text="⏳  Processando...")
        self._show_log()

        existing = self._conv.find_existing(song)

        def task():
            log = lambda msg: self.after(0, self._log_append, msg)
            prog = lambda p: self.after(0, self._set_progress, p)

            # ── Download ──────────────────────────────────────────────────────
            if existing:
                log(f"📂  Música já existe: {existing.name}")
                log("🔍  Verificando compatibilidade...")
                compat = self._conv.check_compat(existing)
                log(compat.summary())
                if compat.compatible:
                    log("🔄  Forçando re-processamento...")
                downloaded_path = str(existing)
            else:
                log("⬇   Baixando do Rhythmverse...")
                downloaded_path = self._client.download_song(song, progress_cb=prog)
                if not downloaded_path:
                    self.after(0, self._on_done, None, "❌  Download falhou")
                    return
                log(f"✅  Download concluído")

            # ── Convert / fix ─────────────────────────────────────────────────
            prog(0)
            result = self._conv.process_folder(song, Path(downloaded_path), log)

            # ── Verify ────────────────────────────────────────────────────────
            if result and result.is_dir():
                compat = self._conv.check_compat(result)
                if compat.compatible:
                    log("🎸  Pronta para o YARG! Faça Scan Songs.")
                    self.after(0, self._on_done, result, None)
                else:
                    log(f"⚠️   {compat.summary()}")
                    self.after(0, self._on_done, None, "Conversão incompleta")
            else:
                self.after(0, self._on_done, None, "Falha na conversão")

        threading.Thread(target=task, daemon=True).start()

    def _on_done(self, folder: Optional[Path], error: Optional[str]) -> None:
        self._processing = False
        self._set_progress(0)

        if folder:
            self._action_btn.config(
                text="✅  No YARG — faça Scan Songs!",
                bg="#1E4A2A", fg=SUCCESS, state="normal",
            )
            self._compat_var.set(f"✅  Pronta: {folder.name}")
            # Refresh list icons
            if self._selected:
                self._do_refresh_list_item()
        else:
            self._action_btn.config(
                text=f"❌  {error or 'Erro'}",
                bg="#4A1E1E", fg=ERR, state="normal",
            )

    def _do_refresh_list_item(self) -> None:
        """Atualiza o ícone da música selecionada na lista."""
        sel = self._lb.curselection()
        if not sel or not self._selected:
            return
        idx  = sel[0]
        song = self._selected
        self._lb.delete(idx)
        icon = "✅"
        fmt  = f"[{song.gameformat.upper()[:5]}]"
        name = song.artist + " — " + song.title if song.artist else song.title
        self._lb.insert(idx, f"  {icon}  {fmt:<7}  {name}")
        self._lb.selection_set(idx)
        self._lb.itemconfig(idx, fg=SUCCESS)

    # ── Format filter ─────────────────────────────────────────────────────────

    def _set_format(self, fmt: str) -> None:
        if fmt == self._gameformat:
            return
        self._gameformat = fmt
        self._page = 1
        for f, btn in self._fmt_btns.items():
            clr = FMT_CLR.get(f, DIM)
            if f == fmt:
                btn.config(bg=clr, fg="white")
            else:
                btn.config(bg=CARD, fg=DIM)
        self._do_search()

    def _go_page(self, delta: int) -> None:
        new = self._page + delta
        if 1 <= new <= self._total_pages and not self._loading:
            self._page = new
            self._do_search()

    # ── Log panel ─────────────────────────────────────────────────────────────

    def _show_log(self) -> None:
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
        if not self._log.winfo_ismapped():
            self._log.pack(fill="x", padx=16, pady=4,
                           before=self._compat_lbl)

    def _hide_log(self) -> None:
        self._log.pack_forget()

    def _log_append(self, msg: str) -> None:
        self._log.config(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.config(state="disabled")

    # ── Progress ──────────────────────────────────────────────────────────────

    def _set_progress(self, val: float) -> None:
        if val > 0:
            if not self._prog.winfo_ismapped():
                self._prog.pack(fill="x", padx=10, pady=(0, 4), before=self._detail)
            self._prog["value"] = val * 100
        else:
            self._prog.pack_forget()
            self._prog["value"] = 0

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _open_web(self) -> None:
        if self._selected:
            url = (self._selected.song_page_url
                   or self._selected.download_page_url
                   or f"https://rhythmverse.co/songfile/{self._selected.id}")
            webbrowser.open(url)

    def _get_query(self) -> str:
        t = self._q_var.get().strip()
        return "" if t in ("", "Buscar artista, título, charter...") else t

    def _ph_in(self, ph: str) -> None:
        if self._q_var.get() == ph:
            self._search_entry.delete(0, "end")
            self._search_entry.config(fg=TEXT)

    def _ph_out(self, ph: str) -> None:
        if not self._q_var.get():
            self._search_entry.insert(0, ph)
            self._search_entry.config(fg=DIM)

    @staticmethod
    def _sep(parent: tk.Widget) -> None:
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16, pady=6)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def _check_deps() -> bool:
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import bs4  # noqa: F401
    except ImportError:
        missing.append("beautifulsoup4")

    if missing:
        print("❌  Dependências faltando:")
        print(f"    pip3 install {' '.join(missing)}")
        return False

    # Check external tools
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"⚠️   '{tool}' não encontrado no PATH — conversão de áudio pode falhar")
            print("    Instale via: brew install ffmpeg")

    if not ONYX_CLI.exists():
        print(f"⚠️   Onyx CLI não encontrado em {ONYX_CLI}")
        print("    Conversão de RB3 estará indisponível")

    return True


if __name__ == "__main__":
    if not _check_deps():
        sys.exit(1)

    print("🎸  Fross Song Manager — iniciando...")
    app = App()
    app.mainloop()
