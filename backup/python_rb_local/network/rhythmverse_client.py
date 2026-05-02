"""
Rock Band Local — Rhythmverse Client v2
Usa a API JSON interna de https://rhythmverse.co/songfiles/game
Endpoint: POST /api/{gameformat}/songfiles/list  (data_type=full)
         POST /api/{gameformat}/songfiles/search/live
"""
from __future__ import annotations
import io
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin

import requests


BASE_URL = "https://rhythmverse.co"

# Formatos de jogos disponíveis na plataforma
GAMEFORMATS = {
    "all":     "Todos",
    "chm":     "Clone Hero",
    "yarg":    "YARG",
    "rb3":     "Rock Band 3",
    "rb3xbox": "Rock Band 3 (Xbox 360)",
    "wtde":    "Guitar Hero World Tour DE",
    "tbrb":    "The Beatles: Rock Band",
    "ps":      "Phase Shift",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RVSong:
    id: str                        # file_id único na plataforma
    title: str
    artist: str
    charter: str = ""
    genre: str = ""
    year: int = 0
    album: str = ""
    duration_sec: int = 0
    gameformat: str = ""
    completeness: int = 0          # 0-6 (qualidade do chart)
    audio_type: str = ""           # "full", "stems", etc.
    has_guitar: bool = False
    has_bass: bool = False
    has_drums: bool = False
    has_vocals: bool = False
    has_keys: bool = False
    diff_guitar: int = -1
    diff_bass: int = -1
    diff_drums: int = -1
    diff_vocals: int = -1
    diff_keys: int = -1
    download_url: str = ""         # URL direta (pode ser "none" ou vazia)
    download_page_url: str = ""    # https://rhythmverse.co/download/{file_id}
    song_page_url: str = ""        # https://rhythmverse.co/songfile/{file_id}
    cover_url: str = ""
    downloads: int = 0

    @property
    def display_name(self) -> str:
        return f"{self.artist} – {self.title}" if self.artist else self.title

    @property
    def has_direct_download(self) -> bool:
        """Retorna True se há URL direta de download disponível."""
        return bool(self.download_url) and self.download_url.lower() != "none"


@dataclass
class SearchResult:
    songs: List[RVSong]
    page: int
    total_pages: int
    total_songs: int
    query: str


# ── Client ────────────────────────────────────────────────────────────────────

class RhythmverseClient:
    """
    Cliente para a API JSON interna do Rhythmverse.co.

    Endpoints descobertos via engenharia reversa do JS do site:
      POST /api/{gameformat}/songfiles/list         → lista paginada
      POST /api/{gameformat}/songfiles/search/live  → busca por texto
    """

    def __init__(self, config: Dict, download_dir: str = "songs"):
        rv_cfg = config.get('rhythmverse', {})
        self.base_url      = rv_cfg.get('base_url', BASE_URL).rstrip('/')
        self.download_dir  = rv_cfg.get('download_path', download_dir)
        self.records_per_page = rv_cfg.get('records_per_page', 25)
        self._cache_ttl    = rv_cfg.get('cache_ttl_seconds', 120)

        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.base_url}/songfiles/game',
            'Origin': self.base_url,
        })
        self._cache: Dict[str, tuple] = {}  # key → (timestamp, data)

    # ── Pública: busca ─────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        page: int = 1,
        gameformat: str = "all",
        records: int = 0,
    ) -> SearchResult:
        """
        Busca músicas. Se query vazio, lista todas (ordenadas por data).
        gameformat: 'all', 'chm', 'yarg', 'rb3xbox', etc.
        """
        records = records or self.records_per_page
        gameformat = gameformat or "all"

        if query.strip():
            return self._do_search(query.strip(), page, gameformat, records)
        else:
            return self._do_list(page, gameformat, records)

    def get_featured(self, gameformat: str = "all", limit: int = 20) -> List[RVSong]:
        """Retorna músicas recentes em destaque."""
        result = self._do_list(page=1, gameformat=gameformat, records=limit)
        return result.songs

    # ── Pública: download ──────────────────────────────────────────────────────

    def download_song(
        self,
        song: RVSong,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> Optional[str]:
        """
        Baixa e extrai a música na pasta de destino.
        Retorna o caminho da pasta extraída, ou None em caso de erro.
        """
        url = self._resolve_download_url(song)
        if not url:
            print(f"[Rhythmverse] Sem URL de download para '{song.title}'")
            return None

        safe_name = self._safe_folder_name(f"{song.artist} - {song.title}")
        dest_dir  = os.path.join(self.download_dir, safe_name)

        if os.path.exists(dest_dir):
            print(f"[Rhythmverse] Já baixada: {dest_dir}")
            return dest_dir

        os.makedirs(dest_dir, exist_ok=True)

        try:
            resp = self._session.get(url, stream=True, timeout=60,
                                     allow_redirects=True)
            resp.raise_for_status()

            total = int(resp.headers.get('content-length', 0))
            buf = io.BytesIO()
            downloaded = 0

            for chunk in resp.iter_content(chunk_size=16384):
                if chunk:
                    buf.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(downloaded / total)

            buf.seek(0)

            if zipfile.is_zipfile(buf):
                buf.seek(0)
                self._extract_zip(buf, dest_dir)
            elif self._is_rar(buf):
                # .rar: salvar e tentar extrair com unrar se disponível
                buf.seek(0)
                rar_path = os.path.join(dest_dir, "download.rar")
                with open(rar_path, 'wb') as f:
                    f.write(buf.read())
                self._try_extract_rar(rar_path, dest_dir)
            else:
                # Arquivo único — descobrir extensão
                ext = self._extension_from_response(resp, '.bin')
                buf.seek(0)
                with open(os.path.join(dest_dir, f"download{ext}"), 'wb') as f:
                    f.write(buf.read())

            if progress_cb:
                progress_cb(1.0)

            print(f"[Rhythmverse] Download concluído: {dest_dir}")
            return dest_dir

        except Exception as e:
            print(f"[Rhythmverse] Erro ao baixar '{song.title}': {e}")
            shutil.rmtree(dest_dir, ignore_errors=True)
            return None

    # ── Privado: chamadas à API ────────────────────────────────────────────────

    def _do_list(self, page: int, gameformat: str, records: int) -> SearchResult:
        cache_key = f"list:{gameformat}:{page}:{records}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        endpoint = f"{gameformat}/songfiles/list"
        payload  = {
            'data_type': 'full',
            'page':      str(page),
            'records':   str(records),
            'sort[0][sort_by]':    'update_date',
            'sort[0][sort_order]': 'DESC',
        }
        data = self._post_api(endpoint, payload)
        if data is None:
            return SearchResult(songs=[], page=page, total_pages=1, total_songs=0, query="")

        result = self._parse_api_response(data, page, query="")
        self._set_cache(cache_key, result)
        return result

    def _do_search(self, query: str, page: int, gameformat: str, records: int) -> SearchResult:
        cache_key = f"search:{gameformat}:{query}:{page}:{records}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        endpoint = f"{gameformat}/songfiles/search/live"
        payload  = {
            'data_type': 'full',
            'text':      query,
            'page':      str(page),
            'records':   str(records),
        }
        data = self._post_api(endpoint, payload)
        if data is None:
            return SearchResult(songs=[], page=page, total_pages=1, total_songs=0, query=query)

        result = self._parse_api_response(data, page, query=query)
        self._set_cache(cache_key, result)
        return result

    def _post_api(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        url = f"{self.base_url}/api/{endpoint}"
        try:
            resp = self._session.post(url, data=payload, timeout=20)
            resp.raise_for_status()
            # Strip any PHP warnings before JSON
            text = resp.text
            json_start = text.find('{')
            if json_start < 0:
                print(f"[Rhythmverse] Resposta vazia de {endpoint}")
                return None
            import json
            parsed = json.loads(text[json_start:])
            if parsed.get('status') != 'success':
                msg = parsed.get('error', {}).get('message', 'unknown')
                print(f"[Rhythmverse] API error: {msg}")
                return None
            return parsed.get('data')
        except Exception as e:
            print(f"[Rhythmverse] Erro em POST {endpoint}: {e}")
            return None

    # ── Privado: parsing ───────────────────────────────────────────────────────

    def _parse_api_response(self, data: Dict, page: int, query: str) -> SearchResult:
        records_meta = data.get('records', {})
        total_filtered = records_meta.get('total_filtered', 0)
        records_count  = int(data.get('pagination', {}).get('records', self.records_per_page))
        total_pages    = max(1, (total_filtered + records_count - 1) // records_count) if records_count else 1

        songs: List[RVSong] = []
        for entry in data.get('songs', []):
            song = self._parse_song_entry(entry)
            if song:
                songs.append(song)

        return SearchResult(
            songs=songs,
            page=page,
            total_pages=min(total_pages, 2500),
            total_songs=total_filtered,
            query=query,
        )

    def _parse_song_entry(self, entry: Dict) -> Optional[RVSong]:
        """Converte uma entrada da API em RVSong."""
        try:
            file_data = entry.get('file', {})
            song_data = entry.get('data', {})

            file_id = file_data.get('file_id', '')
            if not file_id:
                return None

            # Instrumentos presentes (baseado em dificuldades ≥ 0)
            def has_inst(key: str) -> bool:
                v = file_data.get(key, -1)
                return v is not None and int(v) >= 0

            # URLs
            download_url = file_data.get('download_url', '') or ''
            if download_url.lower() in ('none', 'false', '0', ''):
                download_url = ''
            elif not download_url.startswith('http'):
                download_url = self.base_url + download_url

            dl_page = file_data.get('download_page_url_full', '') or (
                f"{self.base_url}/download/{file_id}"
            )
            song_page = file_data.get('file_url_full', '') or (
                f"{self.base_url}/songfile/{file_id}"
            )

            # Capa
            cover = file_data.get('album_art', '')
            if cover and not cover.startswith('http'):
                cover = self.base_url + cover

            return RVSong(
                id=file_id,
                title=file_data.get('file_title', '') or song_data.get('title', ''),
                artist=file_data.get('file_artist', '') or song_data.get('artist', ''),
                charter=file_data.get('user_folder', '') or file_data.get('user', ''),
                genre=file_data.get('file_genre', '') or '',
                year=int(file_data.get('file_year', 0) or 0),
                album=file_data.get('file_album', '') or '',
                duration_sec=int(file_data.get('file_song_length', 0) or 0),
                gameformat=file_data.get('gameformat', ''),
                completeness=int(file_data.get('completeness', 0) or 0),
                audio_type=file_data.get('audio_type', ''),
                has_guitar=has_inst('diff_guitar'),
                has_bass=has_inst('diff_bass'),
                has_drums=has_inst('diff_drums'),
                has_vocals=has_inst('diff_vocals'),
                has_keys=has_inst('diff_keys'),
                diff_guitar=int(file_data.get('diff_guitar', -1) or -1),
                diff_bass=int(file_data.get('diff_bass', -1) or -1),
                diff_drums=int(file_data.get('diff_drums', -1) or -1),
                diff_vocals=int(file_data.get('diff_vocals', -1) or -1),
                diff_keys=int(file_data.get('diff_keys', -1) or -1),
                download_url=download_url,
                download_page_url=dl_page,
                song_page_url=song_page,
                cover_url=cover,
                downloads=int(file_data.get('downloads', 0) or 0),
            )
        except Exception as e:
            print(f"[Rhythmverse] Erro ao parsear entrada: {e}")
            return None

    # ── Privado: download helpers ──────────────────────────────────────────────

    def _resolve_download_url(self, song: RVSong) -> Optional[str]:
        """Determina a melhor URL para download."""
        if song.has_direct_download:
            return song.download_url
        # Tentar scrape da página de download para encontrar link externo
        if song.download_page_url:
            url = self._scrape_download_page(song.download_page_url)
            if url:
                return url
        return None

    def _scrape_download_page(self, page_url: str) -> Optional[str]:
        """Extrai URL de download da página /download/{file_id}."""
        try:
            resp = self._session.get(page_url, timeout=15)
            resp.raise_for_status()
            # Buscar link de download direto
            patterns = [
                r'href="(https?://[^"]+\.(zip|rar|7z)[^"]*)"',
                r'href="(https?://www\.dropbox\.com[^"]+)"',
                r'href="(https?://drive\.google\.com[^"]+)"',
                r'href="(https?://[^"]+/download[^"]*)"',
                r'"external_url":"([^"]+)"',
            ]
            for pat in patterns:
                m = re.search(pat, resp.text, re.IGNORECASE)
                if m:
                    return m.group(1)
        except Exception as e:
            print(f"[Rhythmverse] Erro ao scrape {page_url}: {e}")
        return None

    def _extract_zip(self, buf: io.BytesIO, dest_dir: str) -> None:
        """Extrai ZIP mantendo estrutura de pastas correta."""
        with zipfile.ZipFile(buf) as zf:
            members = zf.namelist()
            common = os.path.commonprefix(members).rstrip('/')
            if common and all(m.startswith(common + '/') or m == common for m in members):
                tmp_dir = dest_dir + '_tmp'
                zf.extractall(tmp_dir)
                inner = os.path.join(tmp_dir, common)
                if os.path.isdir(inner):
                    shutil.rmtree(dest_dir, ignore_errors=True)
                    shutil.move(inner, dest_dir)
                shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                zf.extractall(dest_dir)

    def _try_extract_rar(self, rar_path: str, dest_dir: str) -> None:
        """Tenta extrair RAR com unrar/7z se disponível."""
        import subprocess
        for cmd in [['unrar', 'x', '-y', rar_path, dest_dir + '/'],
                    ['7z', 'x', rar_path, f'-o{dest_dir}', '-y']]:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0:
                    os.remove(rar_path)
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        print(f"[Rhythmverse] RAR não extraído (unrar/7z ausente): {rar_path}")

    @staticmethod
    def _is_rar(buf: io.BytesIO) -> bool:
        buf.seek(0)
        header = buf.read(7)
        buf.seek(0)
        return header[:4] == b'Rar!'

    @staticmethod
    def _extension_from_response(resp: requests.Response, default: str = '.bin') -> str:
        cd = resp.headers.get('content-disposition', '')
        m = re.search(r'filename="?([^";]+)"?', cd)
        if m:
            return os.path.splitext(m.group(1))[1] or default
        ct = resp.headers.get('content-type', '')
        ext_map = {'application/zip': '.zip', 'application/x-rar': '.rar',
                   'application/x-7z-compressed': '.7z'}
        return ext_map.get(ct.split(';')[0].strip(), default)

    # ── Privado: cache ─────────────────────────────────────────────────────────

    def _get_cache(self, key: str) -> Optional[SearchResult]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
        return None

    def _set_cache(self, key: str, data: SearchResult) -> None:
        self._cache[key] = (time.time(), data)

    # ── Utilitário ─────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_folder_name(name: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        safe = safe.strip('. ')
        return safe[:120] or 'song'
