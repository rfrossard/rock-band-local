// FrossDownloadMenu.cs — Fross Garage Band (YARG mod)
// In-game Rhythmverse search screen injected via Mono.Cecil.
// Builds a full-screen Canvas overlay at runtime; no prefabs needed.
//
// Compile with patch_fgb.command → FrossDownloadMenu.dll → place in Managed/
// Cecil patches MainMenu.Credits() to call FrossDownloadMenu.Show() instead.
//
// Layout uses two helpers:
//   Band(parent, name, color, topOffset, height)       → full-width, top-anchored row
//   BandBottom(parent, name, color, bottomOffset, h)   → full-width, bottom-anchored row
//   Stretch(rt)                                         → fill parent entirely

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

namespace FrossGarageBand
{
    // ─── Data model ───────────────────────────────────────────────────────────

    [Serializable] public class RvFile {
        public string file_id, file_title, file_artist, file_album;
        public int diff_guitar, diff_bass, diff_drums, diff_vocals, diff_keys, diff_band;
        public string file_url_full, download_page_url_full, gameformat;
        public int completeness, downloads;
    }
    [Serializable] public class RvSong       { public RvFile file; }
    [Serializable] public class RvRecords    { public int total_filtered; public int returned; }
    [Serializable] public class RvPagination { public int records; }
    [Serializable] public class RvData {
        public List<RvSong>   songs      = new List<RvSong>();
        public RvRecords      records    = new RvRecords();
        public RvPagination   pagination = new RvPagination();
    }
    [Serializable] public class RvResponse { public string status; public RvData data = new RvData(); }

    // ─── Main component ───────────────────────────────────────────────────────

    public class FrossDownloadMenu : MonoBehaviour
    {
        // ── Entry point ───────────────────────────────────────────────────────
        public static void Show()
        {
            var go = new GameObject("FrossDownloadMenu");
            DontDestroyOnLoad(go);
            go.AddComponent<FrossDownloadMenu>();
        }

        // ── Config ────────────────────────────────────────────────────────────
        const string API_BASE  = "https://rhythmverse.co/api";
        const int    PAGE_SIZE = 20;

        static readonly string[] FORMATS = { "all", "chm", "yarg", "rb3", "ps", "wtde" };
        static readonly string[] LABELS  = { "Todos", "CH", "YARG", "RB3", "PS", "WTDE" };

        // YARG-matched palette (sampled from Music Library screenshot)
        static readonly Color C_BG       = Hex(0x07101C);  // main background
        static readonly Color C_PANEL    = Hex(0x0D1B2B);  // right panel / top bar
        static readonly Color C_CARD     = new Color(0,0,0,0);        // transparent row (unselected)
        static readonly Color C_CARD_HOV = new Color(1,1,1,0.06f);    // hover tint
        static readonly Color C_CARD_SEL = Hex(0x1478FF);             // selected row — full blue
        static readonly Color C_ACCENT   = Hex(0x1478FF);             // accent blue
        static readonly Color C_BTN      = Hex(0x142036);             // button background
        static readonly Color C_TEXT     = Hex(0xFFFFFF);             // primary text — pure white
        static readonly Color C_SUB      = Hex(0x7B8EA8);             // secondary text — gray-blue
        static readonly Color C_GREEN2   = Hex(0x00DC3C);             // download button green
        static readonly Color C_SEP      = new Color(1,1,1,0.06f);    // row separator

        // ── State ─────────────────────────────────────────────────────────────
        string       _query  = "";
        string       _format = "all";
        int          _page   = 1;
        int          _pages  = 1;
        bool         _loading = false;
        bool         _dlBusy  = false;
        List<RvFile> _songs   = new List<RvFile>();
        int          _selIdx  = -1;

        // ── UI refs ───────────────────────────────────────────────────────────
        Transform        _listContent;
        ScrollRect       _scrollRect;
        Text             _statusTxt, _pageTxt;
        Text             _detailTitle, _detailArtist, _detailMeta, _dlStatusTxt;
        GameObject       _loadingCover;
        Image            _dlBar;
        Button           _dlBtn, _prevBtn, _nextBtn;
        InputField       _searchInput;
        List<Button>     _fmtBtns  = new List<Button>();
        List<GameObject> _cards    = new List<GameObject>();
        List<Image>      _borders  = new List<Image>();   // left-border strip per card

        // ── Lifecycle ─────────────────────────────────────────────────────────
        void Awake() { BuildUI(); }
        void Start()  { StartCoroutine(Fetch()); }

        // ═══════════════════════════════════════════════════════════════════════
        //  UI CONSTRUCTION
        // ═══════════════════════════════════════════════════════════════════════

        void BuildUI()
        {
            // Canvas
            var cvGo = new GameObject("FGB_Canvas");
            cvGo.transform.SetParent(transform);
            var cv = cvGo.AddComponent<Canvas>();
            cv.renderMode = RenderMode.ScreenSpaceOverlay;
            cv.sortingOrder = 200;
            var sc = cvGo.AddComponent<CanvasScaler>();
            sc.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            sc.referenceResolution = V2(1920, 1080);
            cvGo.AddComponent<GraphicRaycaster>();

            // Fullscreen background
            var bgImg = NewImg(cvGo.transform, "BG", C_BG);
            Stretch(Rt(bgImg));
            var bg = bgImg.transform;

            // ── TOP BAR — 64 px (matches YARG header height) ─────────────────
            var topBar = Band(bg, "TopBar", C_PANEL, 0f, 64f);

            // 3px accent line at very top — matches YARG's red header stripe
            var topLine = NewImg(topBar, "TopLine", C_ACCENT);
            Rt(topLine).anchorMin = V2(0,1); Rt(topLine).anchorMax = V2(1,1);
            Rt(topLine).pivot = V2(.5f,1); Rt(topLine).anchoredPosition = V2(0,0); Rt(topLine).sizeDelta = V2(0,3);

            // "QUICKPLAY" small label above title (matches YARG layout)
            var titleCap = NewTxt(topBar, "DOWNLOAD", C_ACCENT, 11, TextAnchor.LowerLeft);
            Rt(titleCap).anchorMin = V2(0,0.5f); Rt(titleCap).anchorMax = V2(0.5f,1);
            Rt(titleCap).offsetMin = V2(20,0); Rt(titleCap).offsetMax = V2(0,-4);

            var titleT = NewTxt(topBar, "MUSIC LIBRARY", C_TEXT, 26, TextAnchor.UpperLeft);
            Rt(titleT).anchorMin = V2(0,0); Rt(titleT).anchorMax = V2(0.5f,0.5f);
            Rt(titleT).offsetMin = V2(20,4); Rt(titleT).offsetMax = V2(0,0);

            var backBtn = NewBtn(topBar, "< VOLTAR", C_BTN, C_TEXT, 13);
            Rt(backBtn).anchorMin = V2(1,.5f); Rt(backBtn).anchorMax = V2(1,.5f);
            Rt(backBtn).pivot = V2(1,.5f);
            Rt(backBtn).anchoredPosition = V2(-16, 0);
            Rt(backBtn).sizeDelta = V2(120, 38);
            backBtn.onClick.AddListener(() => Destroy(gameObject));

            // ── SEARCH ROW — 48 px ────────────────────────────────────────────
            var searchRow = Band(bg, "SearchRow", C_BG, 64f, 48f);

            // Search box with rounded feel (darker fill, matches YARG search)
            _searchInput = NewInput(searchRow, "🔍  Buscar artista, música...");
            Rt(_searchInput).anchorMin = V2(0,0); Rt(_searchInput).anchorMax = V2(1,1);
            Rt(_searchInput).offsetMin = V2(16,8); Rt(_searchInput).offsetMax = V2(-130,-8);
            _searchInput.onEndEdit.AddListener(s => { if (Input.GetKeyDown(KeyCode.Return)) OnSearch(); });

            var srchBtn = NewBtn(searchRow, "BUSCAR", C_ACCENT, C_TEXT, 14);
            Rt(srchBtn).anchorMin = V2(1,0); Rt(srchBtn).anchorMax = V2(1,1);
            Rt(srchBtn).pivot = V2(1,.5f);
            Rt(srchBtn).anchoredPosition = V2(-12,0);
            Rt(srchBtn).sizeDelta = V2(110, 0);
            Rt(srchBtn).offsetMin += V2(0, 8); Rt(srchBtn).offsetMax -= V2(0, 8);
            srchBtn.onClick.AddListener(OnSearch);

            // ── FORMAT ROW — 38 px (filter pills like YARG's TRACK/ARTIST/etc) ──
            var fmtRow = Band(bg, "FmtRow", C_BG, 112f, 38f);

            // Thin separator below search
            var fmtSep = NewImg(fmtRow, "Sep", C_SEP);
            Rt(fmtSep).anchorMin = V2(0,1); Rt(fmtSep).anchorMax = V2(1,1);
            Rt(fmtSep).pivot = V2(0.5f,1); Rt(fmtSep).anchoredPosition = V2(0,0); Rt(fmtSep).sizeDelta = V2(0,1);

            for (int i = 0; i < FORMATS.Length; i++)
            {
                int idx = i;
                bool sel = FORMATS[i] == _format;
                var fb = NewBtn(fmtRow, LABELS[i], sel ? C_ACCENT : new Color(0,0,0,0), sel ? C_TEXT : C_SUB, 12);
                Rt(fb).anchorMin = V2(0,.5f); Rt(fb).anchorMax = V2(0,.5f);
                Rt(fb).pivot = V2(0,.5f);
                Rt(fb).anchoredPosition = V2(16 + i * 80f, 0);
                Rt(fb).sizeDelta = V2(74, 26);
                _fmtBtns.Add(fb);
                fb.onClick.AddListener(() => OnFormatSelect(idx));
            }

            // ── STATUS ROW — 32 px ───────────────────────────────────────────
            var statusRow = Band(bg, "StatusRow", C_BG, 150f, 32f);

            _statusTxt = NewTxt(statusRow, "Carregando...", C_SUB, 12, TextAnchor.MiddleLeft);
            Rt(_statusTxt).anchorMin = V2(0,0); Rt(_statusTxt).anchorMax = V2(1,1);
            Rt(_statusTxt).offsetMin = V2(16,0); Rt(_statusTxt).offsetMax = V2(-12,0);

            // Thin line under status row (YARG has a subtle divider here)
            var statusSep = NewImg(statusRow, "Sep", C_SEP);
            Rt(statusSep).anchorMin = V2(0,0); Rt(statusSep).anchorMax = V2(1,0);
            Rt(statusSep).pivot = V2(0.5f,0); Rt(statusSep).anchoredPosition = V2(0,0); Rt(statusSep).sizeDelta = V2(0,1);

            // ── PAGINATION ROW — 36 px at bottom ─────────────────────────────
            var pageRow = BandBottom(bg, "PageRow", C_PANEL, 0f, 36f);

            // Top separator on page row
            var pageSep = NewImg(pageRow, "Sep", C_SEP);
            Rt(pageSep).anchorMin = V2(0,1); Rt(pageSep).anchorMax = V2(1,1);
            Rt(pageSep).pivot = V2(0.5f,1); Rt(pageSep).anchoredPosition = V2(0,0); Rt(pageSep).sizeDelta = V2(0,1);

            _prevBtn = NewBtn(pageRow, "◀ Anterior", C_BTN, C_TEXT, 12);
            Rt(_prevBtn).anchorMin = V2(0,0); Rt(_prevBtn).anchorMax = V2(0,1);
            Rt(_prevBtn).pivot = V2(0,.5f);
            Rt(_prevBtn).anchoredPosition = V2(12,0); Rt(_prevBtn).sizeDelta = V2(110,0);
            Rt(_prevBtn).offsetMin += V2(0,6); Rt(_prevBtn).offsetMax -= V2(0,6);
            _prevBtn.onClick.AddListener(OnPrev);

            _pageTxt = NewTxt(pageRow, "Página 1 / 1", C_SUB, 12, TextAnchor.MiddleCenter);
            Rt(_pageTxt).anchorMin = V2(.5f,0); Rt(_pageTxt).anchorMax = V2(.5f,1);
            Rt(_pageTxt).pivot = V2(.5f,.5f);
            Rt(_pageTxt).anchoredPosition = V2(0,0); Rt(_pageTxt).sizeDelta = V2(200,0);

            _nextBtn = NewBtn(pageRow, "Próxima ▶", C_BTN, C_TEXT, 12);
            Rt(_nextBtn).anchorMin = V2(1,0); Rt(_nextBtn).anchorMax = V2(1,1);
            Rt(_nextBtn).pivot = V2(1,.5f);
            Rt(_nextBtn).anchoredPosition = V2(-12,0); Rt(_nextBtn).sizeDelta = V2(110,0);
            Rt(_nextBtn).offsetMin += V2(0,6); Rt(_nextBtn).offsetMax -= V2(0,6);
            _nextBtn.onClick.AddListener(OnNext);

            // ── CONTENT AREA — fills between status and pagination ────────────
            // top = 64(bar)+48(search)+38(fmt)+32(status) = 182px, bottom = 36(page)
            var contentImg = NewImg(bg, "Content", new Color(0,0,0,0));
            Rt(contentImg).anchorMin = V2(0,0); Rt(contentImg).anchorMax = V2(1,1);
            Rt(contentImg).offsetMin = V2(0,36); Rt(contentImg).offsetMax = V2(0,-182);
            var content = contentImg.transform;

            // Left: song list (65% — matches YARG list proportion)
            var listImg = NewImg(content, "List", C_BG);
            Rt(listImg).anchorMin = V2(0,0); Rt(listImg).anchorMax = V2(.65f,1);
            Rt(listImg).offsetMin = V2(0,0); Rt(listImg).offsetMax = V2(0,0);
            BuildScrollList(listImg.transform);

            // Right: detail panel (35% — matches YARG right panel)
            var detailImg = NewImg(content, "Detail", C_PANEL);
            Rt(detailImg).anchorMin = V2(.65f,0); Rt(detailImg).anchorMax = V2(1,1);
            Rt(detailImg).offsetMin = V2(1,0); Rt(detailImg).offsetMax = V2(0,0);
            BuildDetailPanel(detailImg.transform);

            // Vertical separator between list and detail
            var vsep = NewImg(content, "VSep", C_SEP);
            Rt(vsep).anchorMin = V2(.65f,0); Rt(vsep).anchorMax = V2(.65f,1);
            Rt(vsep).pivot = V2(0,.5f); Rt(vsep).anchoredPosition = V2(0,0); Rt(vsep).sizeDelta = V2(1,0);

            // ── LOADING COVER ─────────────────────────────────────────────────
            var lcImg = NewImg(bg, "LoadCover", new Color(0,0,0,.8f));
            Stretch(Rt(lcImg));
            var lcTxt = NewTxt(lcImg.transform, "Carregando...", C_ACCENT, 30, TextAnchor.MiddleCenter);
            Rt(lcTxt).anchorMin = V2(.5f,.5f); Rt(lcTxt).anchorMax = V2(.5f,.5f);
            Rt(lcTxt).pivot = V2(.5f,.5f);
            Rt(lcTxt).anchoredPosition = V2(0,0); Rt(lcTxt).sizeDelta = V2(400,60);
            _loadingCover = lcImg.gameObject;
            _loadingCover.SetActive(false);
        }

        void BuildScrollList(Transform parent)
        {
            // scrollGo  — ScrollRect + thin Image (needs graphic to receive scroll-wheel)
            //   vpGo    — RectMask2D clips children (no alpha/stencil issues)
            //     ctGo  — Content: cards stacked top-to-bottom
            var scrollGo = new GameObject("Scroll");
            scrollGo.transform.SetParent(parent, false);
            var scrollImg = scrollGo.AddComponent<Image>();
            scrollImg.color = new Color(0,0,0,0.004f);   // just enough to receive events
            Stretch((RectTransform)scrollGo.transform);

            // RectMask2D clips by geometry — never has alpha/stencil issues
            var vpGo = new GameObject("Viewport");
            vpGo.transform.SetParent(scrollGo.transform, false);
            vpGo.AddComponent<RectMask2D>();
            var vpRt = (RectTransform)vpGo.transform;
            Stretch(vpRt);

            var ctGo = new GameObject("Content");
            ctGo.transform.SetParent(vpGo.transform, false);
            var ctR = ctGo.AddComponent<RectTransform>();
            ctR.anchorMin     = V2(0, 1);
            ctR.anchorMax     = V2(1, 1);
            ctR.pivot         = V2(0, 1);
            ctR.anchoredPosition = V2(0, 0);
            ctR.sizeDelta     = V2(0, 0);

            _scrollRect = scrollGo.AddComponent<ScrollRect>();
            _scrollRect.viewport        = vpRt;
            _scrollRect.content         = ctR;
            _scrollRect.horizontal      = false;
            _scrollRect.scrollSensitivity = 40;
            _scrollRect.movementType    = ScrollRect.MovementType.Clamped;
            _scrollRect.inertia         = false;

            _listContent = ctGo.transform;
        }

        void BuildDetailPanel(Transform p)
        {
            // ── DOWNLOAD button — full width at top, like YARG's "PLAY SONG" ─
            _dlBtn = NewBtn(p, "⬇  BAIXAR MÚSICA", C_GREEN2, C_BG, 18);
            Rt(_dlBtn).anchorMin = V2(0,1); Rt(_dlBtn).anchorMax = V2(1,1);
            Rt(_dlBtn).pivot = V2(.5f,1);
            Rt(_dlBtn).anchoredPosition = V2(0,-16);
            Rt(_dlBtn).sizeDelta = V2(-32, 56);
            _dlBtn.onClick.AddListener(OnDownload);
            _dlBtn.gameObject.SetActive(false);

            // ── Song title — big, white, below button ──────────────────────
            _detailTitle = NewTxt(p, "Selecione uma\nmúsica na lista", C_TEXT, 22, TextAnchor.UpperLeft);
            PinTop(_detailTitle, 92f, 72f);

            // ── Artist — gray, below title ─────────────────────────────────
            _detailArtist = NewTxt(p, "", C_SUB, 15, TextAnchor.UpperLeft);
            PinTop(_detailArtist, 170f, 26f);

            // ── Thin separator ─────────────────────────────────────────────
            var sep2 = NewImg(p, "Sep", C_SEP);
            PinTop(sep2, 204f, 1f);

            // ── Metadata key/value rows (YARG style) ─────────────────────
            _detailMeta = NewTxt(p, "", C_SUB, 13, TextAnchor.UpperLeft);
            PinTop(_detailMeta, 212f, 300f);

            // ── Status label — at bottom ───────────────────────────────────
            _dlStatusTxt = NewTxt(p, "", C_GREEN2, 12, TextAnchor.LowerLeft);
            Rt(_dlStatusTxt).anchorMin = V2(0,0); Rt(_dlStatusTxt).anchorMax = V2(1,0);
            Rt(_dlStatusTxt).pivot = V2(0,0);
            Rt(_dlStatusTxt).anchoredPosition = V2(16, 16);
            Rt(_dlStatusTxt).sizeDelta = V2(-32, 60);

            // ── Progress bar — thin, just above status ─────────────────────
            var barBg = NewImg(p, "BarBg", C_BTN);
            Rt(barBg).anchorMin = V2(0,0); Rt(barBg).anchorMax = V2(1,0);
            Rt(barBg).pivot = V2(.5f,0);
            Rt(barBg).anchoredPosition = V2(0, 10);
            Rt(barBg).sizeDelta = V2(-32, 4);
            _dlBar = NewImg(barBg.transform, "Fill", C_GREEN2);
            Rt(_dlBar).anchorMin = V2(0,0); Rt(_dlBar).anchorMax = V2(0,1);
            Rt(_dlBar).pivot = V2(0,0);
            Rt(_dlBar).offsetMin = V2(0,0); Rt(_dlBar).offsetMax = V2(0,0);
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  EVENT HANDLERS
        // ═══════════════════════════════════════════════════════════════════════

        void OnSearch()
        {
            _query = _searchInput.text.Trim();
            _page  = 1;
            StartCoroutine(Fetch());
        }

        void OnFormatSelect(int idx)
        {
            _format = FORMATS[idx];
            for (int i = 0; i < _fmtBtns.Count; i++)
            {
                bool sel = i == idx;
                var img = _fmtBtns[i].GetComponent<Image>();
                var txt = _fmtBtns[i].GetComponentInChildren<Text>();
                img.color = sel ? C_ACCENT : new Color(0,0,0,0);
                txt.color = sel ? C_TEXT   : C_SUB;
                var cb = _fmtBtns[i].colors;
                cb.normalColor      = img.color;
                cb.highlightedColor = sel ? Brighten(C_ACCENT, 1.15f) : new Color(1,1,1,0.08f);
                _fmtBtns[i].colors = cb;
            }
            _page = 1;
            StartCoroutine(Fetch());
        }

        void OnPrev() { if (_page > 1)      { _page--; StartCoroutine(Fetch()); } }
        void OnNext() { if (_page < _pages) { _page++; StartCoroutine(Fetch()); } }

        void OnSelect(int idx)
        {
            _selIdx = idx;
            for (int i = 0; i < _cards.Count; i++)
            {
                bool sel = i == _selIdx;
                var img = _cards[i].GetComponent<Image>();
                if (img) img.color = sel ? C_CARD_SEL : C_CARD;
                // Update text colors: white always (readable on both blue and transparent)
            }
            if (idx < 0 || idx >= _songs.Count)
            {
                _dlBtn.gameObject.SetActive(false);
                return;
            }
            var f = _songs[idx];
            _detailTitle.text  = f.file_title  ?? "—";
            _detailArtist.text = f.file_artist ?? "";
            _detailMeta.text   = BuildMeta(f);
            string dlUrl = !string.IsNullOrEmpty(f.file_url_full) ? f.file_url_full
                         : !string.IsNullOrEmpty(f.download_page_url_full) ? f.download_page_url_full : "";
            _dlBtn.gameObject.SetActive(!string.IsNullOrEmpty(dlUrl));
        }

        void OnDownload()
        {
            if (_selIdx < 0 || _selIdx >= _songs.Count) return;
            var f = _songs[_selIdx];
            // Rhythmverse requires browser cookies for actual downloads.
            // Open the download page in the system browser — simplest, most reliable approach.
            string url = !string.IsNullOrEmpty(f.download_page_url_full) ? f.download_page_url_full
                       : !string.IsNullOrEmpty(f.file_url_full) ? f.file_url_full : "";
            if (string.IsNullOrEmpty(url)) return;
            if (!url.StartsWith("http")) url = "https://rhythmverse.co" + url;
            Application.OpenURL(url);
            SetDl($"Abrindo no navegador: {f.file_title}");
            SetBar(1f);
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  API
        // ═══════════════════════════════════════════════════════════════════════

        IEnumerator Fetch()
        {
            if (_loading) yield break;
            _loading = true;
            SetLoading(true);
            _statusTxt.text = "Buscando...";

            string url, body;
            if (!string.IsNullOrEmpty(_query))
            {
                url  = $"{API_BASE}/{_format}/songfiles/search/live";
                body = $"data_type=full&text={Uri.EscapeDataString(_query)}&page={_page}&records={PAGE_SIZE}";
            }
            else
            {
                url  = $"{API_BASE}/{_format}/songfiles/list";
                body = $"data_type=full&page={_page}&records={PAGE_SIZE}" +
                       "&sort%5B0%5D%5Bsort_by%5D=update_date&sort%5B0%5D%5Bsort_order%5D=DESC";
            }

            byte[] raw = Encoding.UTF8.GetBytes(body);
            using (var req = new UnityWebRequest(url, "POST"))
            {
                req.uploadHandler   = new UploadHandlerRaw(raw);
                req.downloadHandler = new DownloadHandlerBuffer();
                req.SetRequestHeader("Content-Type",     "application/x-www-form-urlencoded");
                req.SetRequestHeader("X-Requested-With", "XMLHttpRequest");
                req.SetRequestHeader("Referer",          "https://rhythmverse.co/songfiles/game");
                req.SetRequestHeader("Origin",           "https://rhythmverse.co");
                yield return req.SendWebRequest();

                if (req.result != UnityWebRequest.Result.Success)
                    _statusTxt.text = $"[ERRO HTTP {(int)req.responseCode}] {req.error}";
                else
                    ParseResponse(req.downloadHandler.text, url, (int)req.responseCode);
            }

            _loading = false;
            SetLoading(false);
        }

        void ParseResponse(string json, string reqUrl = "", int httpCode = 200)
        {
            try
            {
                if (string.IsNullOrEmpty(json))
                {
                    _statusTxt.text = $"[ERRO] Resposta vazia (HTTP {httpCode})";
                    return;
                }

                // JsonUtility fails to deserialize the songs List<> from Rhythmverse's
                // complex JSON (deeply-nested author/difficulties objects confuse Mono's
                // JsonUtility).  Use a manual parser for songs; JsonUtility only for
                // the small records/pagination numbers.
                _songs.Clear();
                _songs.AddRange(ExtractSongs(json));

                int totalFiltered = JsonFindInt(json, "total_filtered");
                int returned      = JsonFindInt(json, "returned");
                int total = totalFiltered > 0 ? totalFiltered
                          : returned      > 0 ? returned
                          : _songs.Count;

                // pagination.records is a quoted string "20" in the API
                int perPgIdx = json.IndexOf("\"pagination\"", StringComparison.Ordinal);
                int perPg    = JsonFindInt(json, "records", perPgIdx > 0 ? perPgIdx : 0);
                if (perPg <= 0) perPg = PAGE_SIZE;
                _pages = Mathf.Max(1, Mathf.CeilToInt((float)total / perPg));

                if (_songs.Count == 0)
                    _statusTxt.text = $"Nenhum resultado  (total_f={totalFiltered} ret={returned})";
                else
                    _statusTxt.text = $"{total:N0} musicas  •  Pagina {_page}/{_pages}";

                _pageTxt.text = $"Pagina {_page} / {_pages}";
                _prevBtn.interactable = _page > 1;
                _nextBtn.interactable = _page < _pages;

                RebuildCards();
            }
            catch (Exception ex)
            {
                _statusTxt.text = $"[ERRO parse] {ex.Message}";
                Debug.LogError($"[FGB] ParseResponse: {ex}");
            }
        }

        // ─── Manual JSON helpers ───────────────────────────────────────────────
        // JsonUtility doesn't handle Rhythmverse's complex songs array reliably.
        // These helpers extract only the fields we need.

        // Returns the string/number value of "key": ... in json starting at startAt.
        static string JsonFind(string json, string key, int startAt = 0)
        {
            string search = "\"" + key + "\":";
            int ki = json.IndexOf(search, startAt, StringComparison.Ordinal);
            if (ki < 0) return null;
            int vi = ki + search.Length;
            while (vi < json.Length && (json[vi] == ' ' || json[vi] == '\n' || json[vi] == '\r')) vi++;
            if (vi >= json.Length) return null;
            char first = json[vi];
            if (first == '"')
            {
                vi++;
                int end = vi;
                while (end < json.Length)
                {
                    if (json[end] == '\\') { end += 2; continue; }
                    if (json[end] == '"') break;
                    end++;
                }
                return end >= json.Length ? null : json.Substring(vi, end - vi);
            }
            if (first == 'n') return null; // null literal
            // number or bool — read until delimiter
            int endN = vi;
            while (endN < json.Length && ",}] \n\r\t".IndexOf(json[endN]) < 0) endN++;
            return json.Substring(vi, endN - vi);
        }

        static int JsonFindInt(string json, string key, int startAt = 0)
        {
            string s = JsonFind(json, key, startAt);
            if (s == null) return 0;
            s = s.Trim('"');
            int v; return int.TryParse(s, out v) ? v : 0;
        }

        // Extracts all "file":{...} blocks from the songs array and returns RvFile list.
        static List<RvFile> ExtractSongs(string json)
        {
            var result = new List<RvFile>();
            int songsIdx = json.IndexOf("\"songs\":[", StringComparison.Ordinal);
            if (songsIdx < 0) return result;
            int pos = songsIdx + 9;

            while (pos < json.Length)
            {
                int fileIdx = json.IndexOf("\"file\":{", pos, StringComparison.Ordinal);
                if (fileIdx < 0) break;

                // Also stop if we've passed the songs array closing ]
                int closeBracket = json.IndexOf(']', pos);
                if (closeBracket >= 0 && closeBracket < fileIdx) break;

                // Walk the brace depth to find the end of the file object
                int blockStart = fileIdx + 7; // points to '{'
                int depth = 0;
                int i = blockStart;
                while (i < json.Length)
                {
                    char c = json[i];
                    if (c == '"') // skip string contents
                    {
                        i++;
                        while (i < json.Length)
                        {
                            if (json[i] == '\\') { i += 2; continue; }
                            if (json[i] == '"') break;
                            i++;
                        }
                    }
                    else if (c == '{') depth++;
                    else if (c == '}') { depth--; if (depth == 0) { i++; break; } }
                    i++;
                }
                string fileJson = json.Substring(blockStart, i - blockStart);
                var f = ParseRvFile(fileJson);
                if (f != null && !string.IsNullOrEmpty(f.file_title)) result.Add(f);
                pos = i;
            }
            return result;
        }

        static RvFile ParseRvFile(string j)
        {
            var f = new RvFile();
            f.file_id                = JsonFind(j, "file_id")    ?? "";
            f.file_title             = JsonFind(j, "file_title")  ?? "";
            f.file_artist            = JsonFind(j, "file_artist") ?? "";
            f.file_album             = JsonFind(j, "file_album")  ?? "";
            f.gameformat             = JsonFind(j, "gameformat")  ?? "";
            f.file_url_full          = JsonFind(j, "file_url_full")          ?? "";
            f.download_page_url_full = JsonFind(j, "download_page_url_full") ?? "";
            f.diff_guitar  = JsonFindInt(j, "diff_guitar");
            f.diff_bass    = JsonFindInt(j, "diff_bass");
            f.diff_drums   = JsonFindInt(j, "diff_drums");
            f.diff_vocals  = JsonFindInt(j, "diff_vocals");
            f.diff_keys    = JsonFindInt(j, "diff_keys");
            f.diff_band    = JsonFindInt(j, "diff_band");
            f.completeness = JsonFindInt(j, "completeness");
            f.downloads    = JsonFindInt(j, "downloads");
            return f;
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  CARD LIST
        // ═══════════════════════════════════════════════════════════════════════

        void RebuildCards()
        {
            foreach (var c in _cards) Destroy(c);
            _cards.Clear();
            _borders.Clear();
            _selIdx = -1;

            float cardH = 54f;  // YARG row height
            var ctR = (RectTransform)_listContent;
            ctR.sizeDelta        = V2(0, _songs.Count * cardH);
            ctR.anchoredPosition = V2(0, 0);

            for (int i = 0; i < _songs.Count; i++)
            {
                int idx = i;
                var f = _songs[i];

                var card = NewImg(_listContent, $"C{i}", C_CARD);  // transparent bg
                var cr = Rt(card);
                cr.anchorMin = V2(0,1); cr.anchorMax = V2(1,1);
                cr.pivot     = V2(0,1);
                cr.anchoredPosition = V2(0, -(i * cardH));
                cr.sizeDelta        = V2(0, cardH);

                // Title — white, left 65% of row
                var t = NewTxt(card.transform, f.file_title ?? "—", C_TEXT, 16, TextAnchor.MiddleLeft);
                Rt(t).anchorMin = V2(0,0); Rt(t).anchorMax = V2(0.65f,1); Rt(t).pivot = V2(0,0.5f);
                Rt(t).anchoredPosition = V2(16,0); Rt(t).sizeDelta = V2(-8, 0);
                t.horizontalOverflow = HorizontalWrapMode.Overflow;

                // Artist — gray italic, right 35% of row
                var a = NewTxt(card.transform, f.file_artist ?? "", C_SUB, 14, TextAnchor.MiddleLeft);
                a.fontStyle = FontStyle.Italic;
                Rt(a).anchorMin = V2(0.65f,0); Rt(a).anchorMax = V2(1,1); Rt(a).pivot = V2(0,0.5f);
                Rt(a).anchoredPosition = V2(0,0); Rt(a).sizeDelta = V2(-12, 0);
                a.horizontalOverflow = HorizontalWrapMode.Overflow;

                // Format badge — top-right corner, small blue label
                string fmt = (f.gameformat ?? "").ToUpper();
                if (!string.IsNullOrEmpty(fmt))
                {
                    var fb = NewTxt(card.transform, fmt, C_ACCENT, 10, TextAnchor.UpperRight);
                    Rt(fb).anchorMin = V2(1,1); Rt(fb).anchorMax = V2(1,1); Rt(fb).pivot = V2(1,1);
                    Rt(fb).anchoredPosition = V2(-8,-4); Rt(fb).sizeDelta = V2(50,14);
                }

                // Thin bottom separator
                var sep = NewImg(card.transform, "Sep", C_SEP);
                Rt(sep).anchorMin = V2(0,0); Rt(sep).anchorMax = V2(1,0);
                Rt(sep).pivot = V2(0.5f,0); Rt(sep).anchoredPosition = V2(0,0); Rt(sep).sizeDelta = V2(0,1);

                var btn = card.gameObject.AddComponent<Button>();
                btn.targetGraphic = card;
                var nav = btn.navigation; nav.mode = Navigation.Mode.None; btn.navigation = nav;
                var cb  = btn.colors;
                cb.normalColor      = C_CARD;
                cb.highlightedColor = C_CARD_HOV;
                cb.pressedColor     = C_CARD_SEL;
                cb.selectedColor    = C_CARD_SEL;
                cb.colorMultiplier  = 1f;
                btn.colors = cb;
                btn.onClick.AddListener(() => OnSelect(idx));

                _cards.Add(card.gameObject);
            }

            if (_detailTitle)  _detailTitle.text  = _songs.Count > 0 ? "Selecione uma\nmúsica na lista" : "Nenhum resultado";
            if (_detailArtist) _detailArtist.text = "";
            if (_detailMeta)   _detailMeta.text   = "";
            if (_dlBtn)        _dlBtn.gameObject.SetActive(false);
            if (_dlStatusTxt)  _dlStatusTxt.text  = "";

            ctR.anchoredPosition = V2(0, 0);
            if (_scrollRect != null) _scrollRect.StopMovement();
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  DOWNLOAD
        // ═══════════════════════════════════════════════════════════════════════

        IEnumerator Download(RvFile f)
        {
            _dlBusy = true;
            _dlBtn.gameObject.SetActive(false);
            SetDl($"Iniciando: {f.file_title}...");
            SetBar(0f);

            string destDir = Path.Combine(SongsDir(),
                SanitizeName($"{f.file_artist ?? "unknown"} - {f.file_title ?? f.file_id}"));
            Directory.CreateDirectory(destDir);

            string url = !string.IsNullOrEmpty(f.file_url_full) ? f.file_url_full : f.download_page_url_full;
            if (!url.StartsWith("http")) url = "https://rhythmverse.co" + url;

            using (var req = UnityWebRequest.Get(url))
            {
                req.SetRequestHeader("Referer", "https://rhythmverse.co");
                var op = req.SendWebRequest();
                while (!op.isDone)
                {
                    SetBar(req.downloadProgress * 0.85f);
                    SetDl($"Baixando {(int)(req.downloadProgress * 100)}%...");
                    yield return null;
                }

                if (req.result != UnityWebRequest.Result.Success)
                {
                    SetDl($"Erro: {req.error}");
                    _dlBusy = false;
                    _dlBtn.gameObject.SetActive(true);
                    yield break;
                }

                SetDl("Extraindo..."); SetBar(0.9f);
                yield return null;

                string tmp = Path.Combine(Path.GetTempPath(), $"fgb_{f.file_id}.zip");
                bool ok = false; string err = "";
                try
                {
                    File.WriteAllBytes(tmp, req.downloadHandler.data);
                    if (IsZip(tmp))
                    {
                        System.IO.Compression.ZipFile.ExtractToDirectory(tmp, destDir);
                        ok = true;
                    }
                    else err = "Formato não suportado (somente ZIP automático)";
                }
                catch (Exception ex) { err = ex.Message; Debug.LogError($"[FGB] Extract: {ex}"); }
                finally { try { File.Delete(tmp); } catch { } }

                SetBar(1f);
                SetDl(ok ? $"✓ '{f.file_title}' instalada em songs/" : $"Erro: {err}");
            }

            _dlBusy = false;
            _dlBtn.gameObject.SetActive(true);
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  UTILITY
        // ═══════════════════════════════════════════════════════════════════════

        static string SongsDir()
        {
            string yarg = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                "Library", "Application Support", "YARG", "songs");
            if (Directory.Exists(yarg)) return yarg;

            // Fallback: songs/ next to the .app
            string local = Path.Combine(
                Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath)), "songs");
            Directory.CreateDirectory(local);
            return local;
        }

        static string SanitizeName(string s)
        {
            foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s.Length > 80 ? s.Substring(0, 80) : s;
        }

        static string BuildMeta(RvFile f)
        {
            var sb = new StringBuilder();
            if (!string.IsNullOrEmpty(f.file_album)) sb.AppendLine($"Álbum: {f.file_album}");
            sb.AppendLine($"Formato: {(f.gameformat ?? "—").ToUpper()}");
            void D(string l, int v) { if (v > 0) sb.AppendLine($"  {l}: {v}"); }
            D("Guitarra", f.diff_guitar); D("Baixo", f.diff_bass);
            D("Bateria",  f.diff_drums);  D("Vocal", f.diff_vocals);
            D("Teclas",   f.diff_keys);
            if (f.downloads > 0) sb.AppendLine($"Downloads: {f.downloads:N0}");
            return sb.ToString().TrimEnd();
        }

        static string Chips(RvFile f)
        {
            var p = new List<string>();
            void A(string l, int v) { if (v > 0) p.Add($"{l}{v}"); }
            A("G:", f.diff_guitar); A("B:", f.diff_bass);
            A("D:", f.diff_drums);  A("V:", f.diff_vocals); A("K:", f.diff_keys);
            return string.Join("  ", p);
        }

        static bool IsZip(string path)
        {
            try
            {
                using (var fs = File.OpenRead(path))
                { var b = new byte[4]; fs.Read(b,0,4); return b[0]==0x50 && b[1]==0x4B; }
            }
            catch { return false; }
        }

        void SetLoading(bool on) { if (_loadingCover) _loadingCover.SetActive(on); }
        void SetDl(string s)    { if (_dlStatusTxt)  _dlStatusTxt.text = s; }

        void SetBar(float t)
        {
            if (_dlBar == null) return;
            // Drive fill by changing anchorMax.x from 0→1
            var r = Rt(_dlBar);
            r.anchorMax = V2(Mathf.Clamp01(t), 1f);
            r.offsetMax  = V2(0, 0); // keep offsets zeroed
        }

        // ═══════════════════════════════════════════════════════════════════════
        //  UI FACTORY
        // ═══════════════════════════════════════════════════════════════════════

        static Image NewImg(Transform parent, string name, Color color)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = color;
            return img;
        }

        static Text NewTxt(Transform parent, string text, Color color, int size, TextAnchor align)
        {
            var go = new GameObject("Txt");
            go.transform.SetParent(parent, false);
            var t = go.AddComponent<Text>();
            t.text = text; t.color = color; t.fontSize = size; t.alignment = align;
            t.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow   = VerticalWrapMode.Overflow;
            return t;
        }

        static Button NewBtn(Transform parent, string label, Color bgColor, Color fgColor, int size)
        {
            var go = new GameObject(label);
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = bgColor;
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            var nav = btn.navigation; nav.mode = Navigation.Mode.None; btn.navigation = nav;
            var cb = btn.colors;
            cb.normalColor      = bgColor;
            cb.highlightedColor = Brighten(bgColor, 1.25f);
            cb.pressedColor     = Brighten(bgColor, 0.75f);
            cb.selectedColor    = bgColor;
            cb.colorMultiplier  = 1f;
            btn.colors = cb;

            var lblGo = new GameObject("Lbl"); lblGo.transform.SetParent(go.transform, false);
            var txt = lblGo.AddComponent<Text>();
            txt.text = label; txt.color = fgColor; txt.fontSize = size;
            txt.alignment = TextAnchor.MiddleCenter;
            txt.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            var tr = Rt(txt);
            tr.anchorMin = V2(0,0); tr.anchorMax = V2(1,1);
            tr.offsetMin = V2(4,0); tr.offsetMax = V2(-4,0);
            return btn;
        }

        static InputField NewInput(Transform parent, string placeholder)
        {
            var go = new GameObject("Input"); go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>(); img.color = Hex(0x2D2D42);

            var tGo = new GameObject("Text"); tGo.transform.SetParent(go.transform, false);
            var txt = tGo.AddComponent<Text>();
            txt.color = C_TEXT; txt.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            txt.fontSize = 16; txt.alignment = TextAnchor.MiddleLeft;
            var tr = Rt(txt); tr.anchorMin=V2(0,0); tr.anchorMax=V2(1,1);
            tr.offsetMin=V2(10,2); tr.offsetMax=V2(-10,-2);

            var pGo = new GameObject("PH"); pGo.transform.SetParent(go.transform, false);
            var ph = pGo.AddComponent<Text>();
            ph.text = placeholder; ph.color = new Color(.5f,.5f,.65f,.8f);
            ph.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            ph.fontSize = 16; ph.alignment = TextAnchor.MiddleLeft; ph.fontStyle = FontStyle.Italic;
            var pr = Rt(ph); pr.anchorMin=V2(0,0); pr.anchorMax=V2(1,1);
            pr.offsetMin=V2(10,2); pr.offsetMax=V2(-10,-2);

            var field = go.AddComponent<InputField>();
            field.targetGraphic = img; field.textComponent = txt; field.placeholder = ph;
            field.caretColor = C_ACCENT;
            return field;
        }

        // ── RectTransform helpers ─────────────────────────────────────────────

        static RectTransform Rt(Component c) => (RectTransform)c.transform;

        static void Stretch(RectTransform r)
        {
            r.anchorMin = V2(0,0); r.anchorMax = V2(1,1);
            r.offsetMin = V2(0,0); r.offsetMax = V2(0,0);
        }

        // Full-width band anchored to TOP of parent
        // topOffset = distance from parent's top to this element's top edge (px, positive = down)
        static Transform Band(Transform parent, string name, Color color, float topOffset, float height)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>(); img.color = color;
            var r = Rt(img);
            r.anchorMin = V2(0, 1); r.anchorMax = V2(1, 1);
            r.pivot = V2(0.5f, 1);
            r.anchoredPosition = V2(0, -topOffset);
            r.sizeDelta = V2(0, height);
            return go.transform;
        }

        // Full-width band anchored to BOTTOM of parent
        static Transform BandBottom(Transform parent, string name, Color color, float bottomOffset, float height)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>(); img.color = color;
            var r = Rt(img);
            r.anchorMin = V2(0, 0); r.anchorMax = V2(1, 0);
            r.pivot = V2(0.5f, 0);
            r.anchoredPosition = V2(0, bottomOffset);
            r.sizeDelta = V2(0, height);
            return go.transform;
        }

        // Pin element to top of parent, full width with 14px side padding
        static void PinTop(Component c, float topOffset, float height)
        {
            var r = Rt(c);
            r.anchorMin = V2(0, 1); r.anchorMax = V2(1, 1);
            r.pivot = V2(0.5f, 1);
            r.anchoredPosition = V2(0, -topOffset);
            r.sizeDelta = V2(-28, height);
        }

        static Vector2 V2(float x, float y) => new Vector2(x, y);
        static Color   Brighten(Color c, float f) => new Color(c.r*f, c.g*f, c.b*f, c.a);
        static Color   Hex(uint rgb) => new Color(
            ((rgb >> 16) & 0xFF) / 255f,
            ((rgb >>  8) & 0xFF) / 255f,
            ( rgb        & 0xFF) / 255f, 1f);
    }
}
