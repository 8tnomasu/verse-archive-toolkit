# VerseArchiveToolkit

`VerseArchiveToolkit` 是整個工具集合與 repository 名稱，用於建立、整理、維護與人工翻譯 verse archive JSON。

## 專案包含的產品

- `VerseArchiveCurator`：桌面端建庫與 archive 維護工具。
- `VerseArchiveTranslator Desktop`：桌面端人工翻譯與編修工具。
- `VerseArchiveTranslator Mobile`：Flutter Android 人工翻譯與編修工具。

## 命名原則

- `VerseArchiveToolkit` 只指整個 repository、umbrella project 與工具集合。
- `VerseArchiveCurator` 是桌面端建庫工具的正式產品名稱。
- `VerseArchiveTranslator` 是翻譯工具的統一產品名稱，桌面版與 Flutter Android 版共用此名稱。
- `verse-archive-toolkit`、`verse_archive_toolkit` 與既有 CLI 指令名稱為相容性保留，不因產品命名調整而變更。

## 從 Windows Release ZIP 開始使用

1. 到 GitHub Releases 下載最新的 Windows ZIP。
2. 將 ZIP 解壓縮到本機資料夾。
3. 執行 `VerseArchiveCurator.exe` 來建立或維護 archive JSON。
4. 如果需要抓取哲思語錄，先填入 `ZenQuotes API key`。
5. 選擇輸出資料夾與建庫選項後開始建庫。
6. 建庫完成後，可從 Curator 內開啟 `VerseArchiveTranslator.exe`，或直接執行它來進行人工翻譯與編修。

## 各程式用途

- `VerseArchiveCurator` 會從 PoetryDB 與 ZenQuotes 抓取資料，套用 review / reject 過濾規則，並輸出 archive JSON。
- `VerseArchiveTranslator Desktop` 可搜尋、檢視、審閱並人工編輯 `title.cn`、`author.cn` 與 `content.cn`。
- `VerseArchiveTranslator Mobile` 在 Android 上延續相同的人工翻譯流程，並支援本機同步資料夾工作模式。

## Python 開發安裝

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

如果需要安裝打包相關依賴：

```bash
python -m pip install -e .[packaging]
```

## 啟動入口

- `verse-archive-gui`：啟動 `VerseArchiveCurator`。
- `verse-archive-translator`：啟動 `VerseArchiveTranslator Desktop`。
- `verse-archive`：CLI 入口，用於建庫、統計與路徑診斷。

## Portable 目錄結構

所有執行期資料都會存放在 portable 應用程式資料夾旁：

```text
app-root/
  data/
    settings.json
  logs/
    builder-gui-*.log
    translator-gui-*.log
  output/
    english_poems.json
    philosophy_quotes.json
```

- `data/`：只存放本機設定。
- `logs/`：存放桌面應用程式的執行日誌。
- `output/`：存放產生出的 archive JSON。

Flutter Android App 可以直接使用 archive `output/` 資料夾，也可以使用包含 `output/` 的 portable `VerseArchiveToolkit` 根目錄。

## CLI 與技術名稱說明

CLI 與 Python package 仍保留相容性導向的技術名稱：

- package 名稱：`verse-archive-toolkit`
- import path：`verse_archive_toolkit`
- CLI 指令：`verse-archive`
- GUI 指令：`verse-archive-gui`

這些名稱會保留，以避免破壞既有的開發流程、安裝腳本與自動化設定。

## 驗證

桌面 / Python 驗證：

```bash
python -m pytest
```

Flutter Android 驗證，請在 `apps/verse_archive_translator_flutter` 目錄下執行：

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

## 打包

建立 Windows Release 版桌面應用程式：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

建立 Debug 版：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

Release 打包輸出的產品名稱為：

- `VerseArchiveCurator`
- `VerseArchiveTranslator`

## Flutter Android App

Android 版翻譯器位於 `apps/verse_archive_translator_flutter/`，是 `VerseArchiveTranslator` 的行動版。

相關文件：

- App README：`apps/verse_archive_translator_flutter/README.md`
- 桌面翻譯器分析：`docs/analysis/verse_archive_translator_desktop_analysis.md`
- 架構說明：`docs/architecture/flutter-android-verse-archive-translator.md`
- 相容性說明：`docs/compatibility/verse-archive-translator-mobile-compatibility.md`
- Roadmap：`docs/roadmap/flutter-android-verse-archive-translator-roadmap.md`

## 備註

- `ZenQuotes API key` 請只保留在本機，不要提交到版本庫。
- 本次命名整理不會變更 JSON schema、archive 讀寫語意、translator 保存語意、搜尋語意或 random-pick 語意。
