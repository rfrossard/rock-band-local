// FrossDownloadMenu.cs — Fross Garage Band (YARG mod)
// In-game Rhythmverse search screen injected via Mono.Cecil.
// Builds a full-screen Canvas overlay at runtime; no prefabs needed.
//
// Compile with patch_fgb.command → FrossDownloadMenu.dll → place in Managed/
// Cecil patches MainMenu.Credits() to call FrossDownloadMenu.Show() instead.

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
    // ─── Data types ───────────────────────────────────────────────────────────

    [Serializable]
    public class RvFile
    {
        public string file_id;
        public string file_title;
        public string file_artist;
        public string file_album;
        public string diff_guitar;
        public string diff_bass;
        public string diff_drums;
        public string diff_vocals;
        public string diff_keys;
        public string download_url;
        public string gameformat;
        public string completeness;
        public int downloads;
    }

    [Serializable]
    public class RvSong    { public RvFile file; }
    [Serializable]
    public class RvRecords { public int total_filtered; }
    [Serializable]
    public class RvPagination { public int records; }
    [Serializable]
    public class RvData
    {
        public List<RvSong> songs = new List<RvSong>();
        public RvRecords records = new RvRecords();
        public RvPagination pagination = new RvPagination();
    }
    [Serializable]
    public class RvResponse { public string status; public RvData data = new RvData(); }

    // ─── Main component ───────────────────────────────────────────────────────

    public class FrossDownloadMenu : MonoBehaviour
    {
        // ── Public entry point ────────────────────────────────────────────────

        public static void Show()
        {
            var go = new GameObject("FrossDownloadMenu");
            DontDestroyOnLoad(go);
            go.AddComponent<FrossDownloadMenu>();
        }

        // ── Config ────────────────────────────────────────────────────────────

        const string API_BASE = "https://rhythmverse.co/api";
        const string API_REFERER = "https://rhythmverse.co/songfiles/game";
        const int RECORDS_PER_PAGE = 20;

        static readonly string[] FORMATS = { "all", "chm", "yarg", "rb3", "ps", "wtde" };
        static readonly string[] FORMAT_LABELS = { "Todos", "CH", "YARG", "RB3", "PS", "WTDE" };

        // YARG dark palette
        static readonly Color C_BG        = new Color(0.07f, 0.07f, 0.10f, 1f);
        static readonly Color C_PANEL     = new Color(0.11f, 0.11f, 0.16f, 1f);
        static readonly Color C_CARD      = new Color(0.14f, 0.14f, 0.20f, 1f);
        static readonly Color C_CARD_SEL  = new Color(0.18f, 0.28f, 0.40f, 1f);
        static readonly Color C_ACCENT    = new Color(0.30f, 0.80f, 0.45f, 1f);  // green
        static readonly Color C_BTN       = new Color(0.20f, 0.20f, 0.28f, 1f);
        static readonly Color C_BTN_HOV   = new Color(0.25f, 0.50f, 0.35f, 1f);
        static readonly Color C_TEXT      = new Color(0.92f, 0.92f, 0.96f, 1f);
        static readonly Color C_SUBTEXT   = new Color(0.55f, 0.55f, 0.65f, 1f);
        static readonly Color C_RED       = new Color(0.85f, 0.25f, 0.25f, 1f);

        // ── State ─────────────────────────────────────────────────────────────

        string _query     = "";
        string _format    = "all";
        int    _page      = 1;
        int    _totalPages = 1;

        List<RvFile> _results = new List<RvFile>();
        int _selectedIdx = -1;
        bool _loading = false;

        // Download state
        bool   _downloading   = false;
        float  _dlProgress    = 0f;
        string _dlStatus      = "";
        string _downloadedTitle = "";

        // ── UI refs ───────────────────────────────────────────────────────────

        Transform _listContainer;
        Text      _statusText;
        Text      _pageText;
        Text      _detailTitle;
        Text      _detailArtist;
        Text      _detailMeta;
        Text      _dlStatusText;
        GameObject _detailPanel;
        GameObject _loadingOverlay;
        Image     _dlProgressBar;
        Button    _dlButton;
        Button    _prevBtn;
        Button    _nextBtn;
        InputField _searchInput;
        readonly List<Button> _fmtButtons = new List<Button>();
        readonly List<GameObject> _cards   = new List<GameObject>();

        // ── Unity lifecycle ───────────────────────────────────────────────────

        void Awake() => BuildUI();

        void Start() => StartCoroutine(FetchResults());

        // ─── UI construction ──────────────────────────────────────────────────

        void BuildUI()
        {
            // Root canvas — renders above everything
            var cvGo = new GameObject("FGB_Canvas");
            cvGo.transform.SetParent(transform);
            var cv = cvGo.AddComponent<Canvas>();
            cv.renderMode = RenderMode.ScreenSpaceOverlay;
            cv.sortingOrder = 200;
            cvGo.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            ((CanvasScaler)cvGo.GetComponent<CanvasScaler>()).referenceResolution = new Vector2(1920, 1080);
            cvGo.AddComponent<GraphicRaycaster>();

            // Full-screen background
            var bg = MakeImage(cvGo.transform, "BG", C_BG);
            FillParent(bg);

            // ── Top bar ──────────────────────────────────────────────────────
            var topBar = MakeImage(bg.transform, "TopBar", C_PANEL);
            SetRect(topBar, 0, 1, 0, 1, 0, -60, 0, 0);

            MakeText(topBar.transform, "📥 Download Music — Rhythmverse",
                     C_ACCENT, 22, TextAnchor.MiddleLeft, new Vector2(20, 0), new Vector2(800, 60));

            var backBtn = MakeButton(topBar.transform, "← Voltar", C_BTN, C_TEXT, 16,
                                     new Vector2(-10, 0), new Vector2(120, 40), TextAnchor.MiddleCenter,
                                     pivot: new Vector2(1, 0.5f), anchorMin: new Vector2(1, 0.5f), anchorMax: new Vector2(1, 0.5f));
            backBtn.onClick.AddListener(() => Destroy(gameObject));

            // ── Search bar row ────────────────────────────────────────────────
            var searchRow = MakeImage(bg.transform, "SearchRow", C_PANEL);
            SetRect(searchRow, 0, 1, 1, 1, 0, -110, 0, -60);

            _searchInput = MakeInputField(searchRow.transform, "Buscar artista, música...",
                                          new Vector2(10, 10), new Vector2(-220, -10),
                                          new Vector2(0, 0), new Vector2(1, 1));

            var searchBtn = MakeButton(searchRow.transform, "🔍 Buscar", C_ACCENT, C_BG, 15,
                                       new Vector2(-10, 10), new Vector2(200, -10),
                                       TextAnchor.MiddleCenter,
                                       pivot: new Vector2(1, 0), anchorMin: new Vector2(1, 0), anchorMax: new Vector2(1, 1));
            searchBtn.onClick.AddListener(OnSearch);
            _searchInput.onEndEdit.AddListener(s => { if (Input.GetKeyDown(KeyCode.Return)) OnSearch(); });

            // ── Format filter row ─────────────────────────────────────────────
            var fmtRow = MakeImage(bg.transform, "FmtRow", new Color(0.09f, 0.09f, 0.13f, 1f));
            SetRect(fmtRow, 0, 1, 1, 1, 0, -150, 0, -110);

            float btnW = 90; float btnH = 30; float startX = 10;
            for (int i = 0; i < FORMATS.Length; i++)
            {
                int idx = i;
                var color = FORMATS[i] == _format ? C_ACCENT : C_BTN;
                var tcolor = FORMATS[i] == _format ? C_BG : C_TEXT;
                var fb = MakeButton(fmtRow.transform, FORMAT_LABELS[i], color, tcolor, 13,
                                    new Vector2(startX + i * (btnW + 6), 8),
                                    new Vector2(btnW, btnH),
                                    TextAnchor.MiddleCenter,
                                    pivot: new Vector2(0, 0), anchorMin: Vector2.zero, anchorMax: Vector2.zero);
                _fmtButtons.Add(fb);
                fb.onClick.AddListener(() => OnFormatSelect(idx));
            }

            // ── Status / count ────────────────────────────────────────────────
            var statusRow = MakeImage(bg.transform, "StatusRow", new Color(0.08f, 0.08f, 0.11f, 1f));
            SetRect(statusRow, 0, 1, 1, 1, 0, -175, 0, -150);
            _statusText = MakeText(statusRow.transform, "Carregando...", C_SUBTEXT, 13,
                                   TextAnchor.MiddleLeft, new Vector2(12, 0), new Vector2(900, 25));

            // ── Main content area ─────────────────────────────────────────────
            // Left: song list  Right: detail panel
            var contentArea = MakeImage(bg.transform, "Content", new Color(0, 0, 0, 0));
            SetRect(contentArea, 0, 1, 0, 1, 0, -30, 0, -175);

            // Song list (left 60%)
            var listPanel = MakeImage(contentArea.transform, "ListPanel", C_BG);
            SetRect(listPanel, 0, 0.60f, 0, 1, 0, 0, 0, 0);

            var scroll = MakeScrollRect(listPanel.transform, out _listContainer);

            // Detail panel (right 40%)
            _detailPanel = MakeImage(contentArea.transform, "DetailPanel", C_PANEL).gameObject;
            SetRect(_detailPanel.transform as RectTransform, 0.60f, 1, 0, 1, 4, 0, 0, 0);

            BuildDetailPanel(_detailPanel.transform);

            // ── Pagination row ────────────────────────────────────────────────
            var pageRow = MakeImage(bg.transform, "PageRow", C_PANEL);
            SetRect(pageRow, 0, 1, 0, 0, 0, 30, 0, 0);

            _prevBtn = MakeButton(pageRow.transform, "◀ Anterior", C_BTN, C_TEXT, 14,
                                  new Vector2(10, 4), new Vector2(130, 22),
                                  TextAnchor.MiddleCenter,
                                  pivot: Vector2.zero, anchorMin: Vector2.zero, anchorMax: new Vector2(0, 1));
            _prevBtn.onClick.AddListener(OnPrev);

            _pageText = MakeText(pageRow.transform, "Página 1 / 1", C_SUBTEXT, 13,
                                 TextAnchor.MiddleCenter, new Vector2(0, 0), new Vector2(200, 30));
            // center it
            var ptRect = _pageText.GetComponent<RectTransform>();
            ptRect.anchorMin = new Vector2(0.5f, 0); ptRect.anchorMax = new Vector2(0.5f, 1);
            ptRect.pivot = new Vector2(0.5f, 0.5f);
            ptRect.anchoredPosition = Vector2.zero;
            ptRect.sizeDelta = new Vector2(200, 0);

            _nextBtn = MakeButton(pageRow.transform, "Próxima ▶", C_BTN, C_TEXT, 14,
                                  new Vector2(-10, 4), new Vector2(130, 22),
                                  TextAnchor.MiddleCenter,
                                  pivot: new Vector2(1, 0), anchorMin: new Vector2(1, 0), anchorMax: Vector2.one);
            _nextBtn.onClick.AddListener(OnNext);

            // ── Loading overlay ───────────────────────────────────────────────
            _loadingOverlay = MakeImage(bg.transform, "Loading", new Color(0, 0, 0, 0.6f)).gameObject;
            FillParent(_loadingOverlay.GetComponent<RectTransform>());
            MakeText(_loadingOverlay.transform, "Carregando...", C_ACCENT, 24,
                     TextAnchor.MiddleCenter, Vector2.zero, new Vector2(400, 60),
                     anchor: new Vector2(0.5f, 0.5f));
            _loadingOverlay.SetActive(false);
        }

        void BuildDetailPanel(Transform parent)
        {
            // Title
            _detailTitle = MakeText(parent, "Selecione uma música", C_TEXT, 18,
                                    TextAnchor.UpperLeft,
                                    new Vector2(14, -12), new Vector2(-14, -12),
                                    anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
            _detailTitle.GetComponent<RectTransform>().sizeDelta = new Vector2(-28, 80);

            _detailArtist = MakeText(parent, "", C_SUBTEXT, 14,
                                     TextAnchor.UpperLeft,
                                     new Vector2(14, -96), new Vector2(-14, -96),
                                     anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
            _detailArtist.GetComponent<RectTransform>().sizeDelta = new Vector2(-28, 40);

            _detailMeta = MakeText(parent, "", new Color(0.65f, 0.75f, 0.65f, 1f), 13,
                                   TextAnchor.UpperLeft,
                                   new Vector2(14, -140), new Vector2(-14, -140),
                                   anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
            _detailMeta.GetComponent<RectTransform>().sizeDelta = new Vector2(-28, 200);

            // Download button
            _dlButton = MakeButton(parent, "⬇  Baixar Música", C_ACCENT, C_BG, 16,
                                   new Vector2(14, 110), new Vector2(-14, 58),
                                   TextAnchor.MiddleCenter,
                                   pivot: new Vector2(0, 0), anchorMin: Vector2.zero, anchorMax: new Vector2(1, 0));
            _dlButton.onClick.AddListener(OnDownload);
            _dlButton.gameObject.SetActive(false);

            // Progress bar background
            var barBg = MakeImage(parent, "BarBg", C_BTN);
            SetRect(barBg, 0, 1, 0, 0, 14, 58, -14, 40);

            // Progress bar fill
            var barFill = MakeImage(barBg.transform, "BarFill", C_ACCENT);
            var fillRect = barFill.GetComponent<RectTransform>();
            fillRect.anchorMin = Vector2.zero; fillRect.anchorMax = new Vector2(0, 1);
            fillRect.pivot = Vector2.zero; fillRect.sizeDelta = new Vector2(0, 0);
            fillRect.anchoredPosition = Vector2.zero;
            _dlProgressBar = barFill;

            // Download status text
            _dlStatusText = MakeText(parent, "", C_SUBTEXT, 12, TextAnchor.MiddleCenter,
                                     new Vector2(14, 26), new Vector2(-14, 14),
                                     anchor: Vector2.zero, anchorMax: new Vector2(1, 0));
            _dlStatusText.GetComponent<RectTransform>().sizeDelta = new Vector2(-28, 26);
        }

        // ─── Event handlers ───────────────────────────────────────────────────

        void OnSearch()
        {
            _query = _searchInput.text.Trim();
            _page = 1;
            StartCoroutine(FetchResults());
        }

        void OnFormatSelect(int idx)
        {
            _format = FORMATS[idx];
            for (int i = 0; i < _fmtButtons.Count; i++)
            {
                var img = _fmtButtons[i].GetComponent<Image>();
                var txt = _fmtButtons[i].GetComponentInChildren<Text>();
                bool sel = i == idx;
                img.color = sel ? C_ACCENT : C_BTN;
                txt.color = sel ? C_BG : C_TEXT;
            }
            _page = 1;
            StartCoroutine(FetchResults());
        }

        void OnPrev() { if (_page > 1) { _page--; StartCoroutine(FetchResults()); } }
        void OnNext() { if (_page < _totalPages) { _page++; StartCoroutine(FetchResults()); } }

        void OnSelectSong(int idx)
        {
            _selectedIdx = idx;
            UpdateCards();
            if (idx < 0 || idx >= _results.Count) return;
            var f = _results[idx];
            _detailTitle.text = f.file_title ?? "—";
            _detailArtist.text = f.file_artist ?? "";
            string meta = BuildMeta(f);
            _detailMeta.text = meta;
            _dlButton.gameObject.SetActive(!_downloading && !string.IsNullOrEmpty(f.download_url));
        }

        void OnDownload()
        {
            if (_selectedIdx < 0 || _selectedIdx >= _results.Count) return;
            var f = _results[_selectedIdx];
            if (string.IsNullOrEmpty(f.download_url)) return;
            StartCoroutine(DownloadSong(f));
        }

        // ─── API coroutines ───────────────────────────────────────────────────

        IEnumerator FetchResults()
        {
            if (_loading) yield break;
            _loading = true;
            SetLoading(true);
            _statusText.text = "Buscando...";

            string endpoint, fmt = _format == "all" ? "all" : _format;
            WWWForm form = new WWWForm();
            form.AddField("data_type", "full");
            form.AddField("page", _page.ToString());
            form.AddField("records", RECORDS_PER_PAGE.ToString());

            if (!string.IsNullOrEmpty(_query))
            {
                endpoint = $"{API_BASE}/{fmt}/songfiles/search/live";
                form.AddField("text", _query);
            }
            else
            {
                endpoint = $"{API_BASE}/{fmt}/songfiles/list";
                form.AddField("sort[0][sort_by]", "update_date");
                form.AddField("sort[0][sort_order]", "DESC");
            }

            using (var req = UnityWebRequest.Post(endpoint, form))
            {
                req.SetRequestHeader("X-Requested-With", "XMLHttpRequest");
                req.SetRequestHeader("Referer", "https://rhythmverse.co/songfiles/game");
                req.SetRequestHeader("Origin", "https://rhythmverse.co");
                yield return req.SendWebRequest();

                if (req.result != UnityWebRequest.Result.Success)
                {
                    _statusText.text = $"Erro: {req.error}";
                }
                else
                {
                    ParseAndDisplay(req.downloadHandler.text);
                }
            }

            _loading = false;
            SetLoading(false);
        }

        void ParseAndDisplay(string json)
        {
            try
            {
                // Unity's JsonUtility doesn't handle nested nulls well — minimal manual parse
                var resp = JsonUtility.FromJson<RvResponse>(json);
                if (resp == null || resp.data == null)
                { _statusText.text = "Resposta inesperada da API."; return; }

                _results = new List<RvFile>();
                if (resp.data.songs != null)
                    foreach (var s in resp.data.songs)
                        if (s?.file != null) _results.Add(s.file);

                int total = resp.data.records?.total_filtered ?? _results.Count;
                int perPage = resp.data.pagination?.records;
                if (perPage <= 0) perPage = RECORDS_PER_PAGE;
                _totalPages = Mathf.Max(1, Mathf.CeilToInt((float)total / perPage));

                _statusText.text = total == 0
                    ? "Nenhuma música encontrada."
                    : $"{total} música(s) encontrada(s)  •  Página {_page}/{_totalPages}";
                _pageText.text = $"Página {_page} / {_totalPages}";
                _prevBtn.interactable = _page > 1;
                _nextBtn.interactable = _page < _totalPages;

                RebuildList();
            }
            catch (Exception ex)
            {
                _statusText.text = $"Erro ao processar: {ex.Message}";
                Debug.LogError($"[FGB] Parse error: {ex}");
            }
        }

        // ─── List rendering ───────────────────────────────────────────────────

        void RebuildList()
        {
            foreach (var c in _cards) Destroy(c);
            _cards.Clear();
            _selectedIdx = -1;
            OnSelectSong(-1);

            if (_results.Count == 0) return;

            float cardH = 62f;
            // Resize content height
            var contentRect = _listContainer.GetComponent<RectTransform>();
            contentRect.sizeDelta = new Vector2(0, _results.Count * cardH);

            for (int i = 0; i < _results.Count; i++)
            {
                int idx = i;
                var f = _results[i];
                var card = MakeImage(_listContainer, $"Card_{i}", C_CARD);
                var r = card.GetComponent<RectTransform>();
                r.anchorMin = new Vector2(0, 1); r.anchorMax = new Vector2(1, 1);
                r.pivot = new Vector2(0, 1);
                r.anchoredPosition = new Vector2(2, -i * cardH);
                r.sizeDelta = new Vector2(-4, cardH - 2);

                // Title
                var t = MakeText(card.transform, f.file_title ?? "—", C_TEXT, 14,
                                 TextAnchor.UpperLeft, new Vector2(8, -6), new Vector2(-8, -6),
                                 anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
                t.GetComponent<RectTransform>().sizeDelta = new Vector2(-16, 22);

                // Artist + format
                string sub = $"{f.file_artist ?? ""}  •  {(f.gameformat ?? "").ToUpper()}";
                var a = MakeText(card.transform, sub, C_SUBTEXT, 12,
                                 TextAnchor.UpperLeft, new Vector2(8, -30), new Vector2(-8, -30),
                                 anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
                a.GetComponent<RectTransform>().sizeDelta = new Vector2(-16, 18);

                // Difficulty chips
                string chips = BuildChips(f);
                if (!string.IsNullOrEmpty(chips))
                {
                    var d = MakeText(card.transform, chips, new Color(0.45f, 0.75f, 0.55f, 1f), 11,
                                     TextAnchor.UpperLeft, new Vector2(8, -48), new Vector2(-8, -48),
                                     anchor: new Vector2(0, 1), anchorMax: new Vector2(1, 1));
                    d.GetComponent<RectTransform>().sizeDelta = new Vector2(-16, 14);
                }

                // Click handler via invisible button
                var btn = card.gameObject.AddComponent<Button>();
                btn.targetGraphic = card;
                var nav = btn.navigation; nav.mode = Navigation.Mode.None; btn.navigation = nav;
                ColorBlock cb = btn.colors;
                cb.normalColor = C_CARD; cb.highlightedColor = C_CARD_SEL;
                cb.pressedColor = C_ACCENT; cb.selectedColor = C_CARD_SEL;
                btn.colors = cb;
                btn.onClick.AddListener(() => OnSelectSong(idx));

                _cards.Add(card.gameObject);
            }
        }

        void UpdateCards()
        {
            for (int i = 0; i < _cards.Count; i++)
            {
                var img = _cards[i].GetComponent<Image>();
                if (img != null) img.color = i == _selectedIdx ? C_CARD_SEL : C_CARD;
            }
        }

        // ─── Download ─────────────────────────────────────────────────────────

        IEnumerator DownloadSong(RvFile f)
        {
            _downloading = true;
            _dlButton.gameObject.SetActive(false);
            _dlProgress = 0f;
            _downloadedTitle = f.file_title ?? "música";
            SetDlStatus($"Baixando: {_downloadedTitle}...");
            UpdateProgressBar(0f);

            // Figure out destination folder
            string songsDir = GetSongsDir();
            string safeTitle = SanitizeFileName($"{f.file_artist ?? "unknown"} - {f.file_title ?? f.file_id}");
            string destFolder = Path.Combine(songsDir, safeTitle);
            Directory.CreateDirectory(destFolder);

            string url = f.download_url;
            if (!url.StartsWith("http")) url = "https://rhythmverse.co" + url;

            string tmpFile = Path.Combine(Path.GetTempPath(), $"fgb_{f.file_id}.tmp");

            using (var req = UnityWebRequest.Get(url))
            {
                req.SetRequestHeader("Referer", "https://rhythmverse.co");
                req.downloadHandler = new DownloadHandlerFile(tmpFile);
                var op = req.SendWebRequest();

                while (!op.isDone)
                {
                    _dlProgress = req.downloadProgress;
                    UpdateProgressBar(_dlProgress * 0.9f);
                    SetDlStatus($"Baixando: {(int)(_dlProgress * 100)}%");
                    yield return null;
                }

                if (req.result != UnityWebRequest.Result.Success)
                {
                    SetDlStatus($"Erro: {req.error}");
                    _downloading = false;
                    _dlButton.gameObject.SetActive(true);
                    yield break;
                }
            }

            SetDlStatus("Extraindo...");
            UpdateProgressBar(0.92f);
            yield return null;

            bool extracted = false;
            string error = "";
            try
            {
                ExtractArchive(tmpFile, destFolder);
                extracted = true;
            }
            catch (Exception ex)
            {
                error = ex.Message;
                Debug.LogError($"[FGB] Extract error: {ex}");
            }

            try { File.Delete(tmpFile); } catch { }

            UpdateProgressBar(1f);
            if (extracted)
                SetDlStatus($"✓ '{_downloadedTitle}' instalada em songs/");
            else
                SetDlStatus($"Erro ao extrair: {error}");

            _downloading = false;
            _dlButton.gameObject.SetActive(true);
        }

        void ExtractArchive(string src, string dest)
        {
            // Try .zip first (most common on Rhythmverse)
            if (IsZip(src))
            {
                System.IO.Compression.ZipFile.ExtractToDirectory(src, dest);
                return;
            }
            // For .7z / .rar: shell out to system tools if available
            string ext = Path.GetExtension(src).ToLower();
            throw new Exception($"Formato {ext} não suportado automaticamente. Arquivo salvo em: {dest}");
        }

        static bool IsZip(string path)
        {
            try
            {
                using (var fs = File.OpenRead(path))
                {
                    var buf = new byte[4]; fs.Read(buf, 0, 4);
                    return buf[0] == 0x50 && buf[1] == 0x4B; // PK
                }
            }
            catch { return false; }
        }

        // ─── Helpers ──────────────────────────────────────────────────────────

        static string GetSongsDir()
        {
            // Try YARG's default songs path first
            string yarg = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                "Library", "Application Support", "YARG", "songs");
            if (Directory.Exists(yarg)) return yarg;

            // Fallback: next to the app
            string app = Application.dataPath;
            string parent = Path.GetDirectoryName(Path.GetDirectoryName(app)); // up from .app/Contents
            string local = Path.Combine(parent, "songs");
            Directory.CreateDirectory(local);
            return local;
        }

        static string SanitizeFileName(string s)
        {
            foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s.Length > 80 ? s.Substring(0, 80) : s;
        }

        static string BuildMeta(RvFile f)
        {
            var sb = new StringBuilder();
            if (!string.IsNullOrEmpty(f.file_album)) sb.AppendLine($"Álbum: {f.file_album}");
            sb.AppendLine($"Formato: {(f.gameformat ?? "—").ToUpper()}");
            void Diff(string lbl, string val) { if (!string.IsNullOrEmpty(val) && val != "0") sb.AppendLine($"{lbl}: {val}"); }
            Diff("Guitarra", f.diff_guitar); Diff("Baixo", f.diff_bass);
            Diff("Bateria", f.diff_drums);  Diff("Vocal", f.diff_vocals);
            Diff("Teclas",  f.diff_keys);
            if (f.downloads > 0) sb.AppendLine($"Downloads: {f.downloads:N0}");
            if (!string.IsNullOrEmpty(f.completeness)) sb.AppendLine($"Completeza: {f.completeness}");
            return sb.ToString().TrimEnd();
        }

        static string BuildChips(RvFile f)
        {
            var parts = new List<string>();
            void Add(string icon, string val) { if (!string.IsNullOrEmpty(val) && val != "0") parts.Add($"{icon}{val}"); }
            Add("🎸", f.diff_guitar); Add("🎸b", f.diff_bass);
            Add("🥁", f.diff_drums);  Add("🎤", f.diff_vocals); Add("🎹", f.diff_keys);
            return string.Join("  ", parts);
        }

        void SetLoading(bool on)
        {
            if (_loadingOverlay) _loadingOverlay.SetActive(on);
        }

        void SetDlStatus(string s)
        {
            _dlStatus = s;
            if (_dlStatusText) _dlStatusText.text = s;
        }

        void UpdateProgressBar(float t)
        {
            _dlProgress = t;
            if (_dlProgressBar == null) return;
            var r = _dlProgressBar.GetComponent<RectTransform>();
            var parent = _dlProgressBar.transform.parent.GetComponent<RectTransform>();
            r.sizeDelta = new Vector2(parent.rect.width * Mathf.Clamp01(t), 0);
        }

        // ─── UI factory helpers ───────────────────────────────────────────────

        static Image MakeImage(Transform parent, string name, Color color)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = color;
            go.AddComponent<RectTransform>();
            return img;
        }

        static Text MakeText(Transform parent, string content, Color color, int size,
                              TextAnchor align, Vector2 offsetMin, Vector2 offsetMax,
                              Vector2? anchor = null, Vector2? anchorMax = null)
        {
            var go = new GameObject("Text");
            go.transform.SetParent(parent, false);
            var txt = go.AddComponent<Text>();
            txt.text = content; txt.color = color;
            txt.fontSize = size; txt.alignment = align;
            txt.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            txt.resizeTextForBestFit = false;
            txt.horizontalOverflow = HorizontalWrapMode.Wrap;
            txt.verticalOverflow = VerticalWrapMode.Overflow;
            var r = txt.GetComponent<RectTransform>();
            if (anchor.HasValue) { r.anchorMin = anchor.Value; r.anchorMax = anchorMax ?? anchor.Value; }
            r.anchoredPosition = offsetMin;
            return txt;
        }

        static Button MakeButton(Transform parent, string label, Color bgColor, Color textColor,
                                  int fontSize, Vector2 anchoredPos, Vector2 sizeDelta,
                                  TextAnchor textAlign,
                                  Vector2? pivot = null, Vector2? anchorMin = null, Vector2? anchorMax = null)
        {
            var go = new GameObject(label);
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = bgColor;
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            var nav = btn.navigation; nav.mode = Navigation.Mode.None; btn.navigation = nav;
            ColorBlock cb = btn.colors;
            cb.normalColor = bgColor; cb.highlightedColor = bgColor * 1.2f;
            cb.pressedColor = bgColor * 0.8f; btn.colors = cb;

            var r = go.GetComponent<RectTransform>();
            if (pivot.HasValue) r.pivot = pivot.Value;
            if (anchorMin.HasValue) { r.anchorMin = anchorMin.Value; r.anchorMax = anchorMax ?? anchorMin.Value; }
            r.anchoredPosition = anchoredPos;
            r.sizeDelta = sizeDelta;

            var txtGo = new GameObject("Label"); txtGo.transform.SetParent(go.transform, false);
            var txt = txtGo.AddComponent<Text>();
            txt.text = label; txt.color = textColor; txt.fontSize = fontSize;
            txt.alignment = textAlign; txt.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            var tr = txt.GetComponent<RectTransform>();
            tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one;
            tr.offsetMin = Vector2.zero; tr.offsetMax = Vector2.zero;

            return btn;
        }

        static InputField MakeInputField(Transform parent, string placeholder,
                                          Vector2 oMin, Vector2 oMax,
                                          Vector2 anchorMin, Vector2 anchorMax)
        {
            var go = new GameObject("InputField");
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = new Color(0.18f, 0.18f, 0.24f, 1f);
            var r = go.GetComponent<RectTransform>();
            r.anchorMin = anchorMin; r.anchorMax = anchorMax;
            r.offsetMin = oMin; r.offsetMax = oMax;

            // Text child
            var txtGo = new GameObject("Text"); txtGo.transform.SetParent(go.transform, false);
            var txt = txtGo.AddComponent<Text>();
            txt.color = new Color(0.9f, 0.9f, 0.95f, 1f);
            txt.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            txt.fontSize = 16; txt.alignment = TextAnchor.MiddleLeft;
            var tr = txt.GetComponent<RectTransform>();
            tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one;
            tr.offsetMin = new Vector2(8, 2); tr.offsetMax = new Vector2(-8, -2);

            // Placeholder child
            var phGo = new GameObject("Placeholder"); phGo.transform.SetParent(go.transform, false);
            var ph = phGo.AddComponent<Text>();
            ph.text = placeholder;
            ph.color = new Color(0.5f, 0.5f, 0.6f, 0.8f);
            ph.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            ph.fontSize = 16; ph.alignment = TextAnchor.MiddleLeft;
            ph.fontStyle = FontStyle.Italic;
            var pr = ph.GetComponent<RectTransform>();
            pr.anchorMin = Vector2.zero; pr.anchorMax = Vector2.one;
            pr.offsetMin = new Vector2(8, 2); pr.offsetMax = new Vector2(-8, -2);

            var field = go.AddComponent<InputField>();
            field.targetGraphic = img;
            field.textComponent = txt;
            field.placeholder = ph;
            field.caretColor = new Color(0.3f, 0.8f, 0.45f, 1f);

            return field;
        }

        static ScrollRect MakeScrollRect(Transform parent, out Transform content)
        {
            var go = new GameObject("Scroll");
            go.transform.SetParent(parent, false);
            FillParent(go.GetComponent<RectTransform>() ?? go.AddComponent<RectTransform>());

            var mask = go.AddComponent<Image>(); mask.color = new Color(0, 0, 0, 0.01f);
            go.AddComponent<Mask>().showMaskGraphic = false;

            var sr = go.AddComponent<ScrollRect>();
            sr.horizontal = false;

            // Viewport
            var vp = new GameObject("Viewport"); vp.transform.SetParent(go.transform, false);
            var vpRect = vp.AddComponent<RectTransform>();
            vpRect.anchorMin = Vector2.zero; vpRect.anchorMax = Vector2.one;
            vpRect.sizeDelta = Vector2.zero; vpRect.pivot = new Vector2(0, 1);
            vp.AddComponent<Image>().color = new Color(0, 0, 0, 0);
            vp.AddComponent<Mask>().showMaskGraphic = false;

            // Content
            var ct = new GameObject("Content"); ct.transform.SetParent(vp.transform, false);
            var ctRect = ct.AddComponent<RectTransform>();
            ctRect.anchorMin = new Vector2(0, 1); ctRect.anchorMax = Vector2.one;
            ctRect.pivot = new Vector2(0, 1);
            ctRect.sizeDelta = new Vector2(0, 600);
            ctRect.anchoredPosition = Vector2.zero;

            sr.viewport = vpRect;
            sr.content = ctRect;
            sr.scrollSensitivity = 30;

            content = ct.transform;
            return sr;
        }

        // ─── RectTransform utilities ──────────────────────────────────────────

        static void FillParent(RectTransform r)
        {
            r.anchorMin = Vector2.zero; r.anchorMax = Vector2.one;
            r.offsetMin = Vector2.zero; r.offsetMax = Vector2.zero;
        }

        static void SetRect(Transform t, float axMin, float axMax, float ayMin, float ayMax,
                             float offLeft, float offTop, float offRight, float offBot)
        {
            var r = t as RectTransform ?? t.GetComponent<RectTransform>();
            r.anchorMin = new Vector2(axMin, ayMin);
            r.anchorMax = new Vector2(axMax, ayMax);
            r.offsetMin = new Vector2(offLeft, offBot);
            r.offsetMax = new Vector2(offRight, offTop);
        }

        static void SetRect(RectTransform r, float axMin, float axMax, float ayMin, float ayMax,
                             float offLeft, float offTop, float offRight, float offBot)
            => SetRect((Transform)r, axMin, axMax, ayMin, ayMax, offLeft, offTop, offRight, offBot);
    }
}
