"""
Rock Band Local — Rhythmverse Client
Busca e baixa músicas de https://rhythmverse.co
"""
from __future__ import annotations
import io
import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, urlencode, quote

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://rhythmverse.co"

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RVSong:
    id: str
    title: str
    artist: str
    charter: str = ""
    genre: str = ""
    year: str = ""
    difficulty_guitar: int = 0
    difficulty_drums: int = 0
    difficulty_bass: int = 0
    duration_sec: int = 0
    has_guitar: bool = False
    has_bass: bool = False
    has_drums: bool = False
    has_vocals: bool = False
    download_url: str = ""
    song_url: str = ""
    cover_url: str = ""
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.artist} – {self.title}" if self.artist else self.title


@dataclass
class SearchResult:
    songs: List[RVSong]
    page: int
    total_pages: int
    query: str


# ── Client ────────────────────────────────────────────────────────────────────

class RhythmverseClient:
    """
    Cliente HTTP para Rhythmverse.co.
    Usa scraping da página pública (não há API pública documentada).
    """

    def __init__(self, config: Dict, download_dir: str = "songs"):
        self.base_url = config.get('rhythmverse', {}).get('base_url', BASE_URL)
        self.download_dir = config.get('rhythmverse', {}).get('download_path', download_dir)
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        })
        self._cache: Dict[str, tuple] = {}  # url -> (timestamp, data)
        self._cache_ttl = config.get('rhythmverse', {}).get('cache_ttl_seconds', 300)

    # ── Busca ──────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        page: int = 1,
        instrument: str = "",
        genre: str = "",
    ) -> SearchResult:
        """Busca músicas no Rhythmverse."""
        params: Dict[str, str] = {}
        if query:
            params['search'] = query
        if page > 1:
            params['page'] = str(page)
        if instrument:
            params['instrument'] = instrument

        url = self.base_url + "/songs"
        if params:
            url += '?' + urlencode(params)

        html = self._get_html(url)
        if not html:
            return SearchResult(songs=[], page=page, total_pages=1, query=query)

        return self._parse_song_list(html, query, page)

    def get_featured(self) -> List[RVSong]:
        """Retorna músicas em destaque (página inicial)."""
        html = self._get_html(self.base_url)
        if not html:
            return []
        result = self._parse_song_list(html, "", 1)
        return result.songs[:20]

    def get_song_details(self, song: RVSong) -> RVSong:
        """Busca detalhes extras de uma música específica."""
        if not song.song_url:
            return song
        html = self._get_html(song.song_url)
        if not html:
            return song
        return self._parse_song_detail(html, song)

    # ── Download ───────────────────────────────────────────────────────────────

    def download_song(
        self,
        song: RVSong,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> Optional[str]:
        """
        Baixa e extrai a música.
        Retorna o caminho da pasta da música ou None em caso de erro.
        """
        if not song.download_url:
            song = self.get_song_details(song)
        if not song.download_url:
            print(f"[Rhythmverse] URL de download não encontrada para '{song.title}'")
            return None

        # Pasta destino
        safe_name = self._safe_folder_name(f"{song.artist} - {song.title}")
        dest_dir  = os.path.join(self.download_dir, safe_name)
        if os.path.exists(dest_dir):
            print(f"[Rhythmverse] Música já baixada: {dest_dir}")
            return dest_dir

        os.makedirs(dest_dir, exist_ok=True)

        try:
            resp = self._session.get(song.download_url, stream=True, timeout=60)
            resp.raise_for_status()

            total = int(resp.headers.get('content-length', 0))
            buf = io.BytesIO()
            downloaded = 0

            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    buf.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(downloaded / total)

            buf.seek(0)

            # Extrair ZIP
            if zipfile.is_zipfile(buf):
                buf.seek(0)
                with zipfile.ZipFile(buf) as zf:
                    # Tentar extrair mantendo estrutura
                    members = zf.namelist()
                    # Se todos os arquivos estão em uma subpasta, extrair direto
                    common = os.path.commonprefix(members).rstrip('/')
                    if common and all(m.startswith(common + '/') or m == common for m in members):
                        # Extrair para temp e mover
                        tmp_dir = dest_dir + '_tmp'
                        zf.extractall(tmp_dir)
                        inner = os.path.join(tmp_dir, common)
                        if os.path.isdir(inner):
                            shutil.rmtree(dest_dir, ignore_errors=True)
                            shutil.move(inner, dest_dir)
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                    else:
                        zf.extractall(dest_dir)
            else:
                # Tentar salvar como arquivo único (ex: .chart)
                ext = '.zip'
                if 'content-disposition' in resp.headers:
                    cd = resp.headers['content-disposition']
                    import re
                    m = re.search(r'filename="?([^";]+)"?', cd)
                    if m:
                        ext = os.path.splitext(m.group(1))[1]
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

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_song_list(self, html: str, query: str, page: int) -> SearchResult:
        soup = BeautifulSoup(html, 'html.parser')
        songs: List[RVSong] = []

        # Rhythmverse usa cards de músicas — tentar vários seletores comuns
        selectors = [
            'div.song-card',
            'div.chart-card',
            'article.song',
            'div[class*="song-item"]',
            'div[class*="chart-item"]',
            'li.song',
            'a[href*="/songs/"]',
        ]

        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break

        # Fallback: links para páginas de músicas
        if not items:
            items = soup.find_all('a', href=lambda h: h and '/songs/' in h)

        for item in items[:50]:
            song = self._parse_song_card(item)
            if song:
                songs.append(song)

        # Paginação
        total_pages = 1
        pagination = soup.select_one('nav[class*="pagination"], div[class*="pagination"]')
        if pagination:
            page_links = pagination.find_all('a')
            nums = []
            for a in page_links:
                try:
                    nums.append(int(a.get_text(strip=True)))
                except ValueError:
                    pass
            if nums:
                total_pages = max(nums)

        return SearchResult(songs=songs, page=page, total_pages=total_pages, query=query)

    def _parse_song_card(self, el) -> Optional[RVSong]:
        """Extrai dados de um card de música."""
        try:
            # ID e URL
            href = ''
            if el.name == 'a':
                href = el.get('href', '')
            else:
                a = el.find('a', href=lambda h: h and '/songs/' in h)
                if a:
                    href = a.get('href', '')

            if not href:
                return None

            song_url = href if href.startswith('http') else urljoin(self.base_url, href)
            # ID da URL (ex: /songs/12345 ou /songs/artist/title)
            parts = href.rstrip('/').split('/')
            song_id = parts[-1] if parts else href

            # Título e artista
            title_el  = el.select_one('[class*="title"], h2, h3, .song-name, .name')
            artist_el = el.select_one('[class*="artist"], .artist-name, .artist')
            charter_el = el.select_one('[class*="charter"], .charter')

            title  = title_el.get_text(strip=True)  if title_el  else song_id
            artist = artist_el.get_text(strip=True)  if artist_el else ""
            charter = charter_el.get_text(strip=True) if charter_el else ""

            # Capa
            img = el.find('img')
            cover_url = ''
            if img:
                cover_url = img.get('src', '') or img.get('data-src', '')
                if cover_url and not cover_url.startswith('http'):
                    cover_url = urljoin(self.base_url, cover_url)

            return RVSong(
                id=song_id,
                title=title,
                artist=artist,
                charter=charter,
                song_url=song_url,
                cover_url=cover_url,
            )
        except Exception:
            return None

    def _parse_song_detail(self, html: str, song: RVSong) -> RVSong:
        """Extrai informações da página de detalhe de uma música."""
        soup = BeautifulSoup(html, 'html.parser')

        # Download button
        dl_btn = soup.find('a', href=lambda h: h and ('download' in h or '.zip' in h or '/dl/' in h))
        if dl_btn:
            dl_href = dl_btn.get('href', '')
            song.download_url = dl_href if dl_href.startswith('http') else urljoin(self.base_url, dl_href)

        # Tentar encontrar instrumento flags
        text = soup.get_text()
        song.has_guitar  = 'guitar' in text.lower()
        song.has_bass    = 'bass' in text.lower()
        song.has_drums   = 'drums' in text.lower() or 'drum' in text.lower()
        song.has_vocals  = 'vocal' in text.lower()

        return song

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get_html(self, url: str) -> Optional[str]:
        now = time.time()
        if url in self._cache:
            ts, data = self._cache[url]
            if now - ts < self._cache_ttl:
                return data

        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
            self._cache[url] = (now, html)
            return html
        except requests.RequestException as e:
            print(f"[Rhythmverse] Erro ao buscar {url}: {e}")
            return None

    @staticmethod
    def _safe_folder_name(name: str) -> str:
        import re
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        safe = safe.strip('. ')
        return safe[:120] or 'song'
