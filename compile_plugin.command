#!/bin/bash
# ──────────────────────────────────────────────────────────────
#  Fross Garage Band — Compile BepInEx Plugin
#  Double-click para compilar FrossDownloadMusic.dll
# ──────────────────────────────────────────────────────────────
cd "$(dirname "$0")"

YARG_APP="/Applications/YARG.app"
BEPINEX="$YARG_APP/BepInEx"
PLUGIN_DIR="$BEPINEX/plugins/FrossDownloadMusic"
OUTPUT_DLL="$PLUGIN_DIR/FrossDownloadMusic.dll"
CS_FILE="$PLUGIN_DIR/FrossDownloadMusic.cs"
MANAGED="$YARG_APP/Contents/Resources/Data/Managed"

echo "======================================================"
echo "  Fross Garage Band — BepInEx Plugin Compiler"
echo "======================================================"
echo ""

# ── Find compiler ────────────────────────────────────────────
CSC=""
for c in "$YARG_APP/Contents/Frameworks/MonoBleedingEdge/bin/mcs" \
          /opt/homebrew/bin/mcs /usr/local/bin/mcs \
          /opt/homebrew/bin/csc /usr/local/bin/csc; do
    [ -f "$c" ] && CSC="$c" && break
done
[ -z "$CSC" ] && which mcs &>/dev/null && CSC="$(which mcs)"
[ -z "$CSC" ] && which dotnet &>/dev/null && CSC="dotnet"

if [ -z "$CSC" ]; then
    echo "❌ Nenhum compilador C# encontrado."
    echo "   Instale: brew install mono   ou   brew install --cask dotnet-sdk"
    read -p "Pressione Enter..."; exit 1
fi
echo "✓ Compilador: $CSC"
echo ""

# ── Write C# source ──────────────────────────────────────────
mkdir -p "$PLUGIN_DIR"
cat > "$CS_FILE" << 'CSEOF'
/*
 * Fross Garage Band — Download Music (BepInEx Plugin)
 * =====================================================
 * Cria uma tela nativa dentro do YARG para browsear e
 * baixar músicas do Rhythmverse.co, sem app externa.
 *
 * Ativado ao clicar em "Download Music" no menu do YARG.
 */
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;

namespace FrossDownloadMusic
{
    // ── Plugin entry point ───────────────────────────────────────────────────
    [BepInPlugin("com.frossgarageband.downloadmusic", "Fross Download Music", "2.0.0")]
    public class DownloadMusicPlugin : BaseUnityPlugin
    {
        internal static ManualLogSource Log;
        internal static DownloadMusicPlugin Instance;

        // Songs folder — same path YARG scans
        private static readonly string SongsDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.Personal),
            "Documents", "Claude", "Projects", "Rock Band Local", "songs");

        private void Awake()
        {
            Log      = Logger;
            Instance = this;
            Log.LogInfo("=== Fross Download Music v2.0 — carregando ===");

            Directory.CreateDirectory(SongsDir);

            // Patch Credits menu
            var harmony = new Harmony("com.frossgarageband.downloadmusic");
            PatchCreditsMenu(harmony);
        }

        private void PatchCreditsMenu(Harmony harmony)
        {
            Type creditsType = null;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                try {
                    foreach (var t in asm.GetTypes())
                        if (t.Name.IndexOf("Credits", StringComparison.OrdinalIgnoreCase) >= 0
                            && typeof(MonoBehaviour).IsAssignableFrom(t))
                        { creditsType = t; break; }
                } catch { }
                if (creditsType != null) break;
            }

            if (creditsType == null) {
                Log.LogWarning("CreditsMenu não encontrado — tentando interceptar qualquer navegação para Credits");
                // Fallback: intercept scene load
                UnityEngine.SceneManagement.SceneManager.sceneLoaded += OnSceneLoaded;
                return;
            }

            Log.LogInfo("Patching: " + creditsType.FullName);
            foreach (var methodName in new[] { "Start", "Awake", "OnEnable", "OpenMenu" })
            {
                var m = creditsType.GetMethod(methodName,
                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                if (m == null) continue;
                try {
                    harmony.Patch(m, prefix: new HarmonyMethod(
                        typeof(CreditsMenuPatch).GetMethod("Intercept",
                            BindingFlags.Static | BindingFlags.Public)));
                    Log.LogInfo("  ✓ Patched " + creditsType.Name + "." + methodName);
                    break;
                } catch (Exception ex) {
                    Log.LogWarning("  patch failed on " + methodName + ": " + ex.Message);
                }
            }
        }

        private static void OnSceneLoaded(
            UnityEngine.SceneManagement.Scene scene,
            UnityEngine.SceneManagement.LoadSceneMode mode)
        {
            if (scene.name.IndexOf("credit", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                Log.LogInfo("Credits scene detected → intercepting");
                OpenDownloadScreen();
                UnityEngine.SceneManagement.SceneManager.LoadScene(0); // main menu
            }
        }

        public static void OpenDownloadScreen()
        {
            if (Instance == null) return;
            Instance.StartCoroutine(Instance.ShowScreen());
        }

        private IEnumerator ShowScreen()
        {
            yield return null; // wait one frame for scene to settle
            var go = new GameObject("FrossDownloadMusicScreen");
            DontDestroyOnLoad(go);
            go.AddComponent<DownloadMusicScreen>().Init(SongsDir);
        }

        internal static string SongsDirectory => SongsDir;
    }

    // ── Harmony patch ────────────────────────────────────────────────────────
    public static class CreditsMenuPatch
    {
        public static bool Intercept(MonoBehaviour __instance)
        {
            DownloadMusicPlugin.Log.LogInfo("Credits intercepted → opening Download Music");
            UnityEngine.Object.Destroy(__instance.gameObject);
            DownloadMusicPlugin.OpenDownloadScreen();
            return false;
        }
    }

    // ── Main UI screen ───────────────────────────────────────────────────────
    public class DownloadMusicScreen : MonoBehaviour
    {
        // API
        private const string ApiBase = "https://rhythmverse.co/api";
        private string _gameformat = "all";
        private int    _page       = 1;
        private int    _totalPages = 1;
        private string _query      = "";
        private List<SongEntry> _songs = new List<SongEntry>();
        private int    _selectedIdx = 0;
        private bool   _loading    = false;

        // UI roots
        private Canvas         _canvas;
        private GameObject     _root;
        private Text           _statusText;
        private Transform      _listContent;
        private ScrollRect     _scroll;
        private InputField     _searchField;
        private Text           _detailText;
        private Text           _titleText;
        private Button         _btnDownload;
        private Text           _btnDownloadLabel;

        private string _songsDir;
        private Dictionary<string, float> _dlProgress = new Dictionary<string, float>();

        public void Init(string songsDir)
        {
            _songsDir = songsDir;
            BuildUI();
            StartCoroutine(FetchSongs());
        }

        // ── UI Construction ─────────────────────────────────────────────────
        private void BuildUI()
        {
            // Canvas
            var canvasGo = new GameObject("Canvas");
            canvasGo.transform.SetParent(transform, false);
            _canvas = canvasGo.AddComponent<Canvas>();
            _canvas.renderMode  = RenderMode.ScreenSpaceOverlay;
            _canvas.sortingOrder = 9999;
            var cs = canvasGo.AddComponent<CanvasScaler>();
            cs.uiScaleMode         = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            cs.referenceResolution = new Vector2(1920, 1080);
            cs.screenMatchMode     = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            cs.matchWidthOrHeight  = 0.5f;
            canvasGo.AddComponent<GraphicRaycaster>();

            // Ensure EventSystem
            if (FindObjectOfType<EventSystem>() == null)
            {
                var esGo = new GameObject("EventSystem");
                esGo.AddComponent<EventSystem>();
                esGo.AddComponent<StandaloneInputModule>();
            }

            // Root panel (dark background)
            _root = MakePanel(canvasGo.transform, "Root",
                new Color(0.03f, 0.04f, 0.09f, 0.97f));
            Stretch(_root);

            // ── Header ──────────────────────────────────────────────────────
            var header = MakePanel(_root.transform, "Header", new Color(0.06f, 0.08f, 0.16f, 1f));
            var headerRt = header.GetComponent<RectTransform>();
            headerRt.anchorMin = new Vector2(0, 1);
            headerRt.anchorMax = new Vector2(1, 1);
            headerRt.offsetMin = new Vector2(0, -72);
            headerRt.offsetMax = new Vector2(0,  0);

            _titleText = MakeText(header.transform, "Title",
                "📥  Download Music  —  Rhythmverse",
                28, FontStyle.Bold, Color.white);
            var titleRt = _titleText.GetComponent<RectTransform>();
            titleRt.anchorMin = new Vector2(0.02f, 0.1f);
            titleRt.anchorMax = new Vector2(0.7f,  0.9f);

            // Close button (X)
            var btnClose = MakeButton(_root.transform, "BtnClose", "✕  Fechar",
                new Color(0.5f, 0.1f, 0.1f, 1f), 18, OnClose);
            var bcRt = btnClose.GetComponent<RectTransform>();
            bcRt.anchorMin = new Vector2(0.88f, 0.95f);
            bcRt.anchorMax = new Vector2(0.99f, 0.99f);

            // ── Search bar ───────────────────────────────────────────────────
            var searchPanel = MakePanel(_root.transform, "SearchPanel", new Color(0.1f, 0.1f, 0.2f, 1f));
            var spRt = searchPanel.GetComponent<RectTransform>();
            spRt.anchorMin = new Vector2(0.01f, 0.89f);
            spRt.anchorMax = new Vector2(0.73f, 0.94f);

            _searchField = MakeInputField(searchPanel.transform, "SearchField",
                "Buscar artista, título, charter...");
            Stretch(_searchField.gameObject);
            _searchField.onEndEdit.AddListener(q => { if (Input.GetKeyDown(KeyCode.Return)) DoSearch(q); });

            var btnSearch = MakeButton(_root.transform, "BtnSearch", "🔍 Buscar",
                new Color(0.1f, 0.3f, 0.7f, 1f), 16, () => DoSearch(_searchField.text));
            var bsRt = btnSearch.GetComponent<RectTransform>();
            bsRt.anchorMin = new Vector2(0.74f, 0.89f);
            bsRt.anchorMax = new Vector2(0.86f, 0.94f);

            // ── Format filter buttons ────────────────────────────────────────
            var fmts = new[] {
                ("Todos","all"), ("CH","chm"), ("YARG","yarg"),
                ("RB3","rb3"), ("Phase Shift","ps"), ("WTDE","wtde")
            };
            float fw = 0.12f, fgap = 0.002f, fx = 0.01f;
            foreach (var (label, fmt) in fmts)
            {
                string capturedFmt = fmt;
                var fb = MakeButton(_root.transform, "Fmt_" + fmt, label,
                    fmt == "all" ? new Color(0.1f, 0.35f, 0.15f, 1f) : new Color(0.08f, 0.1f, 0.22f, 1f),
                    14, () => SetFormat(capturedFmt));
                var fbRt = fb.GetComponent<RectTransform>();
                fbRt.anchorMin = new Vector2(fx, 0.84f);
                fbRt.anchorMax = new Vector2(fx + fw - fgap, 0.89f);
                fx += fw;
            }

            // ── Status bar ───────────────────────────────────────────────────
            var statusGo = new GameObject("StatusBar");
            statusGo.transform.SetParent(_root.transform, false);
            _statusText = statusGo.AddComponent<Text>();
            _statusText.font     = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            _statusText.fontSize = 14;
            _statusText.color    = new Color(0.6f, 0.9f, 0.6f, 1f);
            _statusText.text     = "Conectando a Rhythmverse...";
            var stRt = statusGo.AddComponent<RectTransform>();
            stRt.anchorMin = new Vector2(0.01f, 0.81f);
            stRt.anchorMax = new Vector2(0.75f, 0.84f);

            // ── Song list (ScrollRect) ───────────────────────────────────────
            var scrollGo = new GameObject("SongScroll");
            scrollGo.transform.SetParent(_root.transform, false);
            _scroll = scrollGo.AddComponent<ScrollRect>();
            _scroll.horizontal = false;
            var scrollRt = scrollGo.AddComponent<RectTransform>();
            scrollRt.anchorMin = new Vector2(0.01f, 0.08f);
            scrollRt.anchorMax = new Vector2(0.73f, 0.81f);
            scrollRt.offsetMin = Vector2.zero;
            scrollRt.offsetMax = Vector2.zero;

            // Viewport
            var vpGo = new GameObject("Viewport");
            vpGo.transform.SetParent(scrollGo.transform, false);
            var vpImg = vpGo.AddComponent<Image>();
            vpImg.color = new Color(0, 0, 0, 0.01f);
            vpGo.AddComponent<Mask>().showMaskGraphic = false;
            Stretch(vpGo);
            _scroll.viewport = vpGo.GetComponent<RectTransform>();

            // Content
            var contentGo = new GameObject("Content");
            contentGo.transform.SetParent(vpGo.transform, false);
            var vlg = contentGo.AddComponent<VerticalLayoutGroup>();
            vlg.spacing             = 4;
            vlg.childAlignment      = TextAnchor.UpperLeft;
            vlg.childForceExpandWidth  = true;
            vlg.childForceExpandHeight = false;
            var csf = contentGo.AddComponent<ContentSizeFitter>();
            csf.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var contentRt = contentGo.GetComponent<RectTransform>();
            contentRt.anchorMin = new Vector2(0, 1);
            contentRt.anchorMax = new Vector2(1, 1);
            contentRt.pivot     = new Vector2(0.5f, 1);
            contentRt.offsetMin = Vector2.zero;
            contentRt.offsetMax = Vector2.zero;
            _scroll.content = contentRt;
            _listContent    = contentGo.transform;

            // Scrollbar
            var sbGo = new GameObject("Scrollbar");
            sbGo.transform.SetParent(scrollGo.transform, false);
            var sb = sbGo.AddComponent<Scrollbar>();
            sb.direction = Scrollbar.Direction.BottomToTop;
            var sbImg = sbGo.AddComponent<Image>();
            sbImg.color = new Color(0.2f, 0.2f, 0.3f, 0.5f);
            var sbRt = sbGo.GetComponent<RectTransform>();
            sbRt.anchorMin = new Vector2(1, 0); sbRt.anchorMax = new Vector2(1, 1);
            sbRt.offsetMin = new Vector2(-12, 0); sbRt.offsetMax = Vector2.zero;
            var sbHandleArea = new GameObject("SlideArea");
            sbHandleArea.transform.SetParent(sbGo.transform, false);
            var shaRt = sbHandleArea.AddComponent<RectTransform>();
            shaRt.anchorMin = Vector2.zero; shaRt.anchorMax = Vector2.one;
            var sbHandle = new GameObject("Handle");
            sbHandle.transform.SetParent(sbHandleArea.transform, false);
            var sbhImg = sbHandle.AddComponent<Image>();
            sbhImg.color = new Color(0.4f, 0.5f, 0.9f, 0.8f);
            sbhImg.raycastTarget = true;
            sb.targetGraphic = sbhImg;
            sb.handleRect    = sbHandle.GetComponent<RectTransform>();
            _scroll.verticalScrollbar = sb;
            _scroll.verticalScrollbarVisibility = ScrollRect.ScrollbarVisibility.AutoHideAndExpandViewport;

            // ── Detail panel (right side) ────────────────────────────────────
            var detail = MakePanel(_root.transform, "Detail", new Color(0.06f, 0.06f, 0.14f, 1f));
            var detailRt = detail.GetComponent<RectTransform>();
            detailRt.anchorMin = new Vector2(0.74f, 0.08f);
            detailRt.anchorMax = new Vector2(0.99f, 0.88f);

            _detailText = MakeText(detail.transform, "DetailText", "", 14, FontStyle.Normal,
                new Color(0.8f, 0.85f, 1f, 1f));
            var dtRt = _detailText.GetComponent<RectTransform>();
            dtRt.anchorMin = new Vector2(0.05f, 0.05f);
            dtRt.anchorMax = new Vector2(0.95f, 0.95f);
            _detailText.alignment  = TextAnchor.UpperLeft;
            _detailText.verticalOverflow = VerticalWrapMode.Overflow;

            // ── Bottom bar ───────────────────────────────────────────────────
            var btnPrev = MakeButton(_root.transform, "BtnPrev", "◀  Anterior",
                new Color(0.1f, 0.1f, 0.25f, 1f), 16, PrevPage);
            SetAnchors(btnPrev, 0.25f, 0.01f, 0.42f, 0.07f);

            var btnNext = MakeButton(_root.transform, "BtnNext", "Próxima  ▶",
                new Color(0.1f, 0.1f, 0.25f, 1f), 16, NextPage);
            SetAnchors(btnNext, 0.43f, 0.01f, 0.60f, 0.07f);

            _btnDownload = MakeButton(_root.transform, "BtnDownload", "⬇  Baixar",
                new Color(0.05f, 0.35f, 0.1f, 1f), 18, DownloadSelected);
            SetAnchors(_btnDownload.gameObject, 0.74f, 0.01f, 0.99f, 0.07f);
            _btnDownloadLabel = _btnDownload.GetComponentInChildren<Text>();
        }

        // ── API calls ────────────────────────────────────────────────────────
        private void DoSearch(string q)
        {
            _query = q.Trim();
            _page  = 1;
            StartCoroutine(FetchSongs());
        }

        private void SetFormat(string fmt)
        {
            _gameformat = fmt;
            _page = 1;
            StartCoroutine(FetchSongs());
        }

        private void PrevPage()
        {
            if (_page > 1) { _page--; StartCoroutine(FetchSongs()); }
        }

        private void NextPage()
        {
            if (_page < _totalPages) { _page++; StartCoroutine(FetchSongs()); }
        }

        private IEnumerator FetchSongs()
        {
            _loading = true;
            SetStatus("Conectando a Rhythmverse...", new Color(0.4f, 0.7f, 1f, 1f));
            ClearList();

            string endpoint = string.IsNullOrEmpty(_query)
                ? $"{ApiBase}/{_gameformat}/songfiles/list"
                : $"{ApiBase}/{_gameformat}/songfiles/search/live";

            string postBody = string.IsNullOrEmpty(_query)
                ? $"data_type=full&page={_page}&records=25&sort[0][sort_by]=update_date&sort[0][sort_order]=DESC"
                : $"data_type=full&text={Uri.EscapeDataString(_query)}&page={_page}&records=25";

            byte[] bodyBytes = Encoding.UTF8.GetBytes(postBody);
            var req = new UnityEngine.Networking.UnityWebRequest(endpoint,
                UnityEngine.Networking.UnityWebRequest.kHttpVerbPOST);
            req.uploadHandler   = new UnityEngine.Networking.UploadHandlerRaw(bodyBytes);
            req.downloadHandler = new UnityEngine.Networking.DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/x-www-form-urlencoded");
            req.SetRequestHeader("X-Requested-With", "XMLHttpRequest");
            req.SetRequestHeader("Referer", "https://rhythmverse.co/songfiles/game");
            req.SetRequestHeader("User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36");

            yield return req.SendWebRequest();

            if (req.result != UnityEngine.Networking.UnityWebRequest.Result.Success)
            {
                SetStatus("❌ Erro de rede: " + req.error, new Color(1f, 0.3f, 0.3f, 1f));
                _loading = false;
                yield break;
            }

            string json = req.downloadHandler.text;
            int jsonStart = json.IndexOf('{');
            if (jsonStart < 0) { SetStatus("❌ Resposta inválida", Color.red); _loading = false; yield break; }
            json = json.Substring(jsonStart);

            _songs = ParseSongs(json, out int total, out _totalPages);

            string statusMsg = string.IsNullOrEmpty(_query)
                ? $"📂  {total:N0} músicas  —  pág. {_page} / {_totalPages}"
                : $"🔍  {total:N0} resultados para \"{_query}\"  —  pág. {_page} / {_totalPages}";
            SetStatus(statusMsg, new Color(0.4f, 1f, 0.5f, 1f));

            RebuildList();
            _loading = false;
        }

        // ── Download ─────────────────────────────────────────────────────────
        private void DownloadSelected()
        {
            if (_songs == null || _selectedIdx >= _songs.Count) return;
            var song = _songs[_selectedIdx];
            if (_dlProgress.ContainsKey(song.Id)) return;

            if (!string.IsNullOrEmpty(song.DownloadUrl))
                StartCoroutine(DownloadFile(song));
            else
            {
                SetStatus($"⚠  Abrindo página de download: {song.Title}", new Color(1f, 0.8f, 0.3f, 1f));
                Application.OpenURL(song.DownloadPageUrl);
            }
        }

        private IEnumerator DownloadFile(SongEntry song)
        {
            _dlProgress[song.Id] = 0f;
            SetStatus($"⬇  Baixando: {song.Title}...", new Color(1f, 0.85f, 0.2f, 1f));
            if (_btnDownloadLabel) _btnDownloadLabel.text = "Baixando...";

            var req = UnityEngine.Networking.UnityWebRequest.Get(song.DownloadUrl);
            req.downloadHandler = new UnityEngine.Networking.DownloadHandlerBuffer();
            yield return req.SendWebRequest();

            if (req.result != UnityEngine.Networking.UnityWebRequest.Result.Success)
            {
                SetStatus($"❌ Falha: {req.error}", Color.red);
            }
            else
            {
                string safe    = Regex.Replace(song.Artist + " - " + song.Title, @"[<>:""/\\|?*]", "_");
                string destDir = Path.Combine(_songsDir, safe.Length > 120 ? safe.Substring(0, 120) : safe);
                Directory.CreateDirectory(destDir);
                byte[] data = req.downloadHandler.data;
                string ext  = ".zip";
                if (data.Length > 4 && data[0] == 0x52 && data[1] == 0x61 && data[2] == 0x72 && data[3] == 0x21)
                    ext = ".rar";
                string outFile = Path.Combine(destDir, "download" + ext);
                File.WriteAllBytes(outFile, data);

                // Try to unzip
                if (ext == ".zip") TryUnzip(outFile, destDir);

                SetStatus($"✅  Baixado: {song.DisplayName}  →  Abrece no YARG após reiniciar",
                    new Color(0.3f, 1f, 0.4f, 1f));
            }

            _dlProgress.Remove(song.Id);
            if (_btnDownloadLabel) _btnDownloadLabel.text = "⬇  Baixar";
        }

        private static void TryUnzip(string zipFile, string destDir)
        {
            try {
                System.IO.Compression.ZipFile.ExtractToDirectory(zipFile, destDir);
                File.Delete(zipFile);
            } catch (Exception ex) {
                DownloadMusicPlugin.Log.LogWarning("Unzip: " + ex.Message);
            }
        }

        // ── List rendering ────────────────────────────────────────────────────
        private void ClearList()
        {
            foreach (Transform child in _listContent)
                Destroy(child.gameObject);
        }

        private void RebuildList()
        {
            ClearList();
            for (int i = 0; i < _songs.Count; i++)
            {
                int capturedI = i;
                var song = _songs[i];
                bool selected = (i == _selectedIdx);

                var item = MakePanel(_listContent, $"Song_{i}",
                    selected ? new Color(0.15f, 0.18f, 0.38f, 1f) : new Color(0.07f, 0.07f, 0.15f, 1f));
                var itemRt = item.GetComponent<RectTransform>();
                itemRt.sizeDelta = new Vector2(0, 60);

                var btn = item.AddComponent<Button>();
                var colors = btn.colors;
                colors.normalColor      = Color.white;
                colors.highlightedColor = new Color(0.85f, 0.9f, 1f, 1f);
                btn.colors = colors;
                btn.targetGraphic = item.GetComponent<Image>();
                btn.onClick.AddListener(() => SelectSong(capturedI));

                // DL indicator
                string dlIcon = song.HasDirectDownload ? "⬇" : "🔗";
                var dlText = MakeText(item.transform, "DL", dlIcon, 14, FontStyle.Normal,
                    song.HasDirectDownload ? new Color(0.4f, 1f, 0.5f) : new Color(1f, 0.8f, 0.3f));
                var dlRt = dlText.GetComponent<RectTransform>();
                dlRt.anchorMin = new Vector2(0, 0.5f); dlRt.anchorMax = new Vector2(0, 0.5f);
                dlRt.anchoredPosition = new Vector2(16, 0); dlRt.sizeDelta = new Vector2(24, 40);

                // Title
                var titleT = MakeText(item.transform, "Title",
                    Trim(song.Title, 45), 16, FontStyle.Bold, Color.white);
                var titleRt = titleT.GetComponent<RectTransform>();
                titleRt.anchorMin = new Vector2(0.04f, 0.5f); titleRt.anchorMax = new Vector2(0.82f, 1f);

                // Artist / info
                string info = song.Artist;
                if (song.Year > 0) info += $"  ({song.Year})";
                if (song.DurationSec > 0) { int m = song.DurationSec / 60, s = song.DurationSec % 60; info += $"  {m}:{s:00}"; }
                var infoT = MakeText(item.transform, "Info", Trim(info, 55), 13, FontStyle.Normal,
                    new Color(0.6f, 0.65f, 0.8f));
                var infoRt = infoT.GetComponent<RectTransform>();
                infoRt.anchorMin = new Vector2(0.04f, 0); infoRt.anchorMax = new Vector2(0.82f, 0.5f);

                // Format badge
                var badge = MakePanel(item.transform, "Badge", FmtColor(song.GameFormat));
                var badgeRt = badge.GetComponent<RectTransform>();
                badgeRt.anchorMin = new Vector2(0.83f, 0.2f); badgeRt.anchorMax = new Vector2(0.99f, 0.8f);
                var badgeText = MakeText(badge.transform, "BadgeLabel",
                    song.GameFormat.ToUpper(), 11, FontStyle.Bold, Color.white);
                Stretch(badgeText.gameObject);
                badgeText.alignment = TextAnchor.MiddleCenter;
            }

            if (_songs.Count > 0) SelectSong(0);
        }

        private void SelectSong(int idx)
        {
            _selectedIdx = idx;
            RebuildList(); // re-draw to update selection color
            UpdateDetail();
        }

        private void UpdateDetail()
        {
            if (_songs == null || _selectedIdx >= _songs.Count) { _detailText.text = ""; return; }
            var s = _songs[_selectedIdx];
            var sb = new StringBuilder();
            sb.AppendLine($"<b>{s.Title}</b>");
            if (!string.IsNullOrEmpty(s.Artist)) sb.AppendLine(s.Artist);
            if (!string.IsNullOrEmpty(s.Album))  sb.AppendLine($"💿 {s.Album}");
            sb.AppendLine("");
            if (!string.IsNullOrEmpty(s.Charter))  sb.AppendLine($"✍ Charter: {s.Charter}");
            if (!string.IsNullOrEmpty(s.Genre))    sb.AppendLine($"🎵 Gênero: {s.Genre}");
            if (s.Year > 0)                         sb.AppendLine($"📅 Ano: {s.Year}");
            if (s.DurationSec > 0) sb.AppendLine($"⏱ {s.DurationSec / 60}:{s.DurationSec % 60:00}");
            if (s.Downloads > 0)   sb.AppendLine($"⬇ {s.Downloads:N0} downloads");
            sb.AppendLine("");
            if (s.HasGuitar)  sb.AppendLine("🎸 Guitarra");
            if (s.HasBass)    sb.AppendLine("🎸 Baixo");
            if (s.HasDrums)   sb.AppendLine("🥁 Bateria");
            if (s.HasVocals)  sb.AppendLine("🎤 Vocal");
            if (s.HasKeys)    sb.AppendLine("🎹 Keys");
            sb.AppendLine("");
            sb.AppendLine(s.HasDirectDownload
                ? "✅ Download direto disponível"
                : "🔗 Apenas página externa");
            _detailText.text = sb.ToString();
        }

        private void SetStatus(string msg, Color color)
        {
            if (_statusText) { _statusText.text = msg; _statusText.color = color; }
        }

        private void OnClose()
        {
            Destroy(gameObject);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape)) OnClose();
        }

        // ── JSON parser (minimal, no external libs) ───────────────────────────
        private static List<SongEntry> ParseSongs(string json, out int totalSongs, out int totalPages)
        {
            totalSongs  = 0;
            totalPages  = 1;
            var songs   = new List<SongEntry>();

            try {
                var m = Regex.Match(json, @"""total_filtered""\s*:\s*(\d+)");
                if (m.Success) totalSongs = int.Parse(m.Groups[1].Value);

                int records = 25;
                var rm = Regex.Match(json, @"""records""\s*:\s*""?(\d+)""?");
                if (rm.Success) records = Math.Max(1, int.Parse(rm.Groups[1].Value));
                totalPages = Math.Max(1, (totalSongs + records - 1) / records);

                // Extract each song block between "file_id" occurrences
                var fileBlocks = Regex.Matches(json, @"\{[^{}]*""file_id""[^{}]*\}");
                foreach (Match fb in fileBlocks)
                {
                    string block = fb.Value;
                    var s = new SongEntry();
                    s.Id          = ExtractStr(block, "file_id");
                    s.Title       = ExtractStr(block, "file_title");
                    s.Artist      = ExtractStr(block, "file_artist");
                    s.Charter     = ExtractStr(block, "user_folder");
                    s.Genre       = ExtractStr(block, "file_genre");
                    s.Album       = ExtractStr(block, "file_album");
                    s.GameFormat  = ExtractStr(block, "gameformat");
                    s.AudioType   = ExtractStr(block, "audio_type");
                    s.Year        = ExtractInt(block, "file_year");
                    s.DurationSec = ExtractInt(block, "file_song_length");
                    s.Downloads   = ExtractInt(block, "downloads");
                    s.DiffGuitar  = ExtractInt(block, "diff_guitar");
                    s.DiffBass    = ExtractInt(block, "diff_bass");
                    s.DiffDrums   = ExtractInt(block, "diff_drums");
                    s.DiffVocals  = ExtractInt(block, "diff_vocals");
                    s.HasGuitar   = s.DiffGuitar  >= 0;
                    s.HasBass     = s.DiffBass    >= 0;
                    s.HasDrums    = s.DiffDrums   >= 0;
                    s.HasVocals   = s.DiffVocals  >= 0;
                    s.HasKeys     = ExtractInt(block, "diff_keys") >= 0;

                    string dlRaw = ExtractStr(block, "download_url");
                    if (!string.IsNullOrEmpty(dlRaw)
                        && dlRaw.ToLower() != "none" && dlRaw.ToLower() != "false")
                    {
                        s.DownloadUrl = dlRaw.StartsWith("http")
                            ? dlRaw : "https://rhythmverse.co" + dlRaw;
                    }
                    string dlPage = ExtractStr(block, "download_page_url_full");
                    s.DownloadPageUrl = !string.IsNullOrEmpty(dlPage)
                        ? dlPage : $"https://rhythmverse.co/download/{s.Id}";
                    s.SongPageUrl = $"https://rhythmverse.co/songfile/{s.Id}";

                    if (!string.IsNullOrEmpty(s.Id)) songs.Add(s);
                }
            } catch (Exception ex) {
                DownloadMusicPlugin.Log.LogError("ParseSongs: " + ex.Message);
            }

            return songs;
        }

        private static string ExtractStr(string json, string key)
        {
            var m = Regex.Match(json, $"\"{Regex.Escape(key)}\"\\s*:\\s*\"([^\"]*)\"");
            return m.Success ? m.Groups[1].Value : "";
        }

        private static int ExtractInt(string json, string key)
        {
            var m = Regex.Match(json, $"\"{Regex.Escape(key)}\"\\s*:\\s*(-?\\d+)");
            return m.Success ? int.Parse(m.Groups[1].Value) : -1;
        }

        // ── UI helpers ────────────────────────────────────────────────────────
        private static GameObject MakePanel(Transform parent, string name, Color color)
        {
            var go  = new GameObject(name);
            go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>();
            img.color = color;
            go.AddComponent<RectTransform>();
            return go;
        }

        private static Text MakeText(Transform parent, string name, string text,
            int size, FontStyle style, Color color)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var t  = go.AddComponent<Text>();
            t.font      = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            t.text      = text;
            t.fontSize  = size;
            t.fontStyle = style;
            t.color     = color;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow   = VerticalWrapMode.Truncate;
            go.AddComponent<RectTransform>();
            return t;
        }

        private static Button MakeButton(Transform parent, string name, string label,
            Color bgColor, int fontSize, UnityEngine.Events.UnityAction onClick)
        {
            var go  = MakePanel(parent, name, bgColor);
            var btn = go.AddComponent<Button>();
            var img = go.GetComponent<Image>();
            img.raycastTarget = true;
            btn.targetGraphic = img;
            var colors = btn.colors;
            colors.highlightedColor = new Color(
                Mathf.Min(bgColor.r + 0.2f, 1f),
                Mathf.Min(bgColor.g + 0.2f, 1f),
                Mathf.Min(bgColor.b + 0.2f, 1f), 1f);
            colors.pressedColor = new Color(bgColor.r * 0.7f, bgColor.g * 0.7f, bgColor.b * 0.7f, 1f);
            btn.colors = colors;
            btn.onClick.AddListener(onClick);
            var lbl = MakeText(go.transform, "Label", label, fontSize, FontStyle.Bold, Color.white);
            Stretch(lbl.gameObject);
            lbl.alignment = TextAnchor.MiddleCenter;
            go.AddComponent<RectTransform>();
            return btn;
        }

        private static InputField MakeInputField(Transform parent, string name, string placeholder)
        {
            var go = MakePanel(parent, name, new Color(0.12f, 0.12f, 0.22f, 1f));
            var field = go.AddComponent<InputField>();

            var ph = MakeText(go.transform, "Placeholder", placeholder, 14,
                FontStyle.Italic, new Color(0.4f, 0.4f, 0.6f, 1f));
            Stretch(ph.gameObject);
            var phRt = ph.GetComponent<RectTransform>();
            phRt.offsetMin = new Vector2(8, 0); phRt.offsetMax = new Vector2(-8, 0);

            var input = MakeText(go.transform, "Text", "", 14, FontStyle.Normal, Color.white);
            Stretch(input.gameObject);
            var inputRt = input.GetComponent<RectTransform>();
            inputRt.offsetMin = new Vector2(8, 0); inputRt.offsetMax = new Vector2(-8, 0);

            field.textComponent  = input;
            field.placeholder    = ph;
            field.targetGraphic  = go.GetComponent<Image>();
            field.caretWidth     = 2;
            field.caretColor     = Color.white;
            return field;
        }

        private static void Stretch(GameObject go)
        {
            var rt = go.GetComponent<RectTransform>() ?? go.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = Vector2.zero; rt.offsetMax = Vector2.zero;
        }

        private static void SetAnchors(GameObject go, float x0, float y0, float x1, float y1)
        {
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = new Vector2(x0, y0); rt.anchorMax = new Vector2(x1, y1);
            rt.offsetMin = Vector2.zero;         rt.offsetMax = Vector2.zero;
        }

        private static Color FmtColor(string fmt)
        {
            switch (fmt?.ToLower())
            {
                case "chm":     return new Color(0.1f, 0.45f, 0.18f, 1f);
                case "yarg":    return new Color(0.15f, 0.32f, 0.65f, 1f);
                case "rb3":
                case "rb3xbox": return new Color(0.55f, 0.12f, 0.12f, 1f);
                case "ps":      return new Color(0.1f, 0.38f, 0.5f,  1f);
                case "wtde":    return new Color(0.5f, 0.28f, 0.08f, 1f);
                default:        return new Color(0.25f, 0.25f, 0.4f, 1f);
            }
        }

        private static string Trim(string s, int max)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Length <= max ? s : s.Substring(0, max - 1) + "…";
        }
    }

    // ── Data model ──────────────────────────────────────────────────────────
    public class SongEntry
    {
        public string Id, Title, Artist, Charter, Genre, Album;
        public string GameFormat, AudioType;
        public string DownloadUrl, DownloadPageUrl, SongPageUrl;
        public int Year, DurationSec, Downloads;
        public int DiffGuitar = -1, DiffBass = -1, DiffDrums = -1, DiffVocals = -1;
        public bool HasGuitar, HasBass, HasDrums, HasVocals, HasKeys;
        public bool HasDirectDownload => !string.IsNullOrEmpty(DownloadUrl);
        public string DisplayName => string.IsNullOrEmpty(Artist) ? Title : $"{Artist} – {Title}";
    }
}
CSEOF

echo "✓ Código C# escrito."
echo ""

# ── References ──────────────────────────────────────────────
REFS=""
add_ref() { [ -f "$1" ] && REFS="$REFS -r:$1" && printf "  ✓ %s\n" "$(basename $1)" || printf "  ⚠ %s\n" "$(basename $1)"; }
echo "Referências:"
add_ref "$BEPINEX/core/BepInEx.dll"
add_ref "$BEPINEX/core/0Harmony.dll"
add_ref "$MANAGED/UnityEngine.dll"
add_ref "$MANAGED/UnityEngine.CoreModule.dll"
add_ref "$MANAGED/UnityEngine.UI.dll"
add_ref "$MANAGED/UnityEngine.InputLegacyModule.dll"
add_ref "$MANAGED/UnityEngine.IMGUIModule.dll"
add_ref "$MANAGED/UnityEngine.UnityWebRequestModule.dll"
add_ref "$MANAGED/UnityEngine.UnityWebRequestWWWModule.dll"
add_ref "$MANAGED/System.IO.Compression.dll"
add_ref "$MANAGED/System.IO.Compression.FileSystem.dll"
echo ""

# ── Compile ──────────────────────────────────────────────────
echo "⚙  Compilando..."
if [ "$CSC" = "dotnet" ]; then
    TMPDIR="/tmp/FrossPlugin_$$"
    mkdir -p "$TMPDIR"
    cp "$CS_FILE" "$TMPDIR/"
    REF_XML=""
    for dll in "$BEPINEX/core/BepInEx.dll" "$BEPINEX/core/0Harmony.dll" \
               "$MANAGED/UnityEngine.dll" "$MANAGED/UnityEngine.CoreModule.dll" \
               "$MANAGED/UnityEngine.UI.dll" "$MANAGED/UnityEngine.InputLegacyModule.dll" \
               "$MANAGED/UnityEngine.IMGUIModule.dll" \
               "$MANAGED/UnityEngine.UnityWebRequestModule.dll" \
               "$MANAGED/UnityEngine.UnityWebRequestWWWModule.dll" \
               "$MANAGED/System.IO.Compression.dll" \
               "$MANAGED/System.IO.Compression.FileSystem.dll"; do
        [ -f "$dll" ] && REF_XML="$REF_XML<Reference Include=\"$(basename $dll .dll)\"><HintPath>$dll</HintPath></Reference>"
    done
    cat > "$TMPDIR/proj.csproj" << PROJEOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net462</TargetFramework>
    <AssemblyName>FrossDownloadMusic</AssemblyName>
    <Nullable>disable</Nullable>
    <OutputType>Library</OutputType>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    <CopyLocalLockFileAssemblies>false</CopyLocalLockFileAssemblies>
  </PropertyGroup>
  <ItemGroup>$REF_XML</ItemGroup>
</Project>
PROJEOF
    dotnet build "$TMPDIR/proj.csproj" -o "$PLUGIN_DIR" -c Release --nologo 2>&1
    rm -rf "$TMPDIR"
else
    "$CSC" -target:library -out:"$OUTPUT_DLL" -langversion:latest \
        -nowarn:0414,0219,1591 $REFS "$CS_FILE" 2>&1
fi

echo ""
if [ -f "$OUTPUT_DLL" ]; then
    SIZE=$(stat -f%z "$OUTPUT_DLL" 2>/dev/null || stat -c%s "$OUTPUT_DLL")
    echo "✅  FrossDownloadMusic.dll compilado! (${SIZE} bytes)"
    echo "   → $OUTPUT_DLL"
    echo ""
    echo "   IMPORTANTE: lance o YARG via BepInEx para ativar o plugin:"
    echo "   $YARG_APP/run_bepinex.sh"
else
    echo "❌  Falha na compilação — veja os erros acima."
fi

echo ""
read -p "Pressione Enter para fechar..."
