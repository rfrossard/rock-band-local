# Fross Garage Band — Session Skill
> Read this at the start of every session. It contains hard-won lessons about the YARG
> Unity runtime so you don't repeat old mistakes. IMPLEMENTATION_PLAN.md has the roadmap.

---

## Unity / YARG Runtime

| Detail | Value |
|--------|-------|
| Unity version | 2022 (Mono scripting backend) |
| Game path | `/Applications/YARG.app` |
| Managed DLLs | `YARG.app/Contents/Resources/Data/Managed/` |
| CanvasScaler reference | 1920 × 1080 |
| Canvas sortingOrder for overlay | 200 (renders above all YARG UI) |

### DLLs required in FrossDownloadMenu.csproj (net472)
All `<HintPath>MANAGED_PATH/xxx.dll</HintPath>`:
- `UnityEngine.dll`, `UnityEngine.CoreModule.dll`
- `UnityEngine.UI.dll` — Button, Image, ScrollRect, InputField, etc.
- `UnityEngine.UIModule.dll` — Canvas, RenderMode, CanvasScaler, Mask
- `UnityEngine.TextRenderingModule.dll` — TextAnchor, Font, FontStyle, HorizontalWrapMode
- `UnityEngine.JSONSerializeModule.dll` — JsonUtility
- `UnityEngine.InputLegacyModule.dll` — Input (keyboard)
- `UnityEngine.UnityWebRequestModule.dll` — UnityWebRequest, UploadHandlerRaw, DownloadHandlerBuffer
- `System.IO.Compression.FileSystem` (no HintPath — framework)
- `System.IO.Compression` (no HintPath — framework)

### Patcher.csproj MUST have
```xml
<EnableDefaultCompileItems>false</EnableDefaultCompileItems>
...
<Compile Include="Patcher.cs" />
```
Without this MSBuild globs FrossDownloadMenu.cs into the Patcher project (66 errors).

---

## RectTransform Layout Rules (CRITICAL)

**The most common source of bugs.** Unity's RectTransform works as follows:

```
offsetMin = bottom-left offset FROM anchorMin point
offsetMax = top-right offset FROM anchorMax point
```

### ✅ Correct patterns used in FrossDownloadMenu.cs

**Full-width row pinned to TOP** (e.g. top bar, search row):
```csharp
r.anchorMin = new Vector2(0, 1);   // anchor at parent's top edge
r.anchorMax = new Vector2(1, 1);   // anchor at parent's top edge, full width
r.pivot     = new Vector2(0.5f, 1);
r.anchoredPosition = new Vector2(0, -topOffset);  // topOffset px below top
r.sizeDelta        = new Vector2(0, height);       // absolute height
```
→ Creates a `height`-px bar whose top edge is `topOffset` pixels below parent's top.

**Full-width row pinned to BOTTOM** (e.g. pagination):
```csharp
r.anchorMin = new Vector2(0, 0);
r.anchorMax = new Vector2(1, 0);
r.pivot     = new Vector2(0.5f, 0);
r.anchoredPosition = new Vector2(0, bottomOffset);
r.sizeDelta        = new Vector2(0, height);
```

**Fill parent** (stretch element):
```csharp
r.anchorMin = Vector2.zero; r.anchorMax = Vector2.one;
r.offsetMin = Vector2.zero; r.offsetMax = Vector2.zero;
```

**Content area between top bands and bottom band:**
```csharp
r.anchorMin = new Vector2(0, 0); r.anchorMax = new Vector2(1, 1);
r.offsetMin = new Vector2(0, bottomBandHeight);   // e.g. 30
r.offsetMax = new Vector2(0, -topBandsTotal);     // e.g. -174
```

### ❌ Wrong pattern (caused black screen in v2.0.0)
```csharp
// WRONG — creates element filling screen EXCEPT top 60px:
r.anchorMin = new Vector2(0, 0); r.anchorMax = new Vector2(1, 1);
r.offsetMax = new Vector2(0, -60);  // top edge 60px below top, bottom at screen bottom
```

---

## Rhythmverse API

```
POST https://rhythmverse.co/api/{fmt}/songfiles/list
POST https://rhythmverse.co/api/{fmt}/songfiles/search/live

Headers:
  Content-Type: application/x-www-form-urlencoded
  X-Requested-With: XMLHttpRequest
  Referer: https://rhythmverse.co/songfiles/game
  Origin: https://rhythmverse.co

Body (list):   data_type=full&page=N&records=20&sort[0][sort_by]=update_date&sort[0][sort_order]=DESC
Body (search): data_type=full&text=QUERY&page=N&records=20

fmt values: all  chm  yarg  rb3  rb3xbox  wtde  tbrb  ps

Response: { status, data: { songs: [{ file: { file_id, file_title, file_artist,
            file_album, diff_guitar, diff_bass, diff_drums, diff_vocals, diff_keys,
            download_url, gameformat, completeness, downloads } }],
            records: { total_filtered }, pagination: { records } } }
```

**Use `UploadHandlerRaw` + `DownloadHandlerBuffer`** — do NOT use `WWWForm` (requires extra DLL).

---

## Cecil Patch Pipeline

`patch_fgb.command` does:
1. Compiles `FrossDownloadMenu.cs` → `FrossDownloadMenu.dll` (net472, refs YARG DLLs)
2. Copies DLL to `Managed/`
3. Gets Mono.Cecil from NuGet if not present
4. Creates temp `Patcher.cs` + `Patcher.csproj` (net9.0)
5. Patcher reads `Assembly-CSharp.dll.bak_fgb` (clean backup), rewrites `MainMenu.Credits()` body to call `FrossDownloadMenu.Show()`, writes result to `Assembly-CSharp.dll`
6. Re-signs with `codesign -s -`

**Cecil write rule:** write to MemoryStream first, `asm.Dispose()`, then `File.WriteAllBytes()`.
Never read and write the same path simultaneously → EndOfStreamException.

**Always restore from backup before patching** (prevents BadImageFormatException on second run):
```bash
cp "$BAK" "$ASM"
```

**Target method:** `YARG.Menu.Main.MainMenu::Credits()` (0 parameters)

---

## Songs Folder

- YARG reads songs from configured SongFolders in its settings
- `/Users/frossard/Documents/Claude/Projects/Rock Band Local/songs/` — 182 songs, configured in YARG
- `~/Library/Application Support/YARG/songs/` — YARG's default download target
- FrossDownloadMenu downloads to `~/Library/Application Support/YARG/songs/` first

---

## Restore / Rollback

```bash
bash restore_yarg.command   # restores .bak_fgb (our patch) or .bak_dm / .bak_original
```
Run this if audio stops or game regresses after patching.

---

## Visual Identity

| Element | Value |
|---------|-------|
| App name | Fross Garage Band |
| Base game | YARG v0.14.0 |
| Accent color | `#4DC87A` (green) |
| Background | `#12121A` (near-black) |
| Panel | `#1C1C28` |
| Card | `#232333` |
| Text | `#EAEAF5` |
| Subtext | `#888899` |
