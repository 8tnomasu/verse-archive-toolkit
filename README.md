# VerseArchiveToolkit

一套用於建立、整理、維護與人工翻譯 verse archive JSON 的工具集合。

## 這是什麼？

`VerseArchiveToolkit` 是一個包含多個工具的專案，主要用來處理 verse archive JSON 的建立與人工翻譯流程。

這個專案目前包含：

- 桌面端建庫工具 `VerseArchiveCurator`
- 桌面端翻譯工具 `VerseArchiveTranslator Desktop`
- Android 翻譯工具 `VerseArchiveTranslator Mobile`

一般使用流程是先用 `VerseArchiveCurator` 建立或整理 archive JSON，再用 `VerseArchiveTranslator` 進行人工翻譯與編修。

## 名稱說明

- `VerseArchiveToolkit`：整個 repository 與工具集合名稱
- `VerseArchiveCurator`：桌面端建庫與 archive 維護工具
- `VerseArchiveTranslator Desktop`：桌面端人工翻譯與編修工具
- `VerseArchiveTranslator Mobile`：Flutter Android 人工翻譯與編修工具

## 包含的工具

- `VerseArchiveCurator`：從 PoetryDB 與 ZenQuotes 抓取資料、套用過濾規則，並輸出 archive JSON。
- `VerseArchiveTranslator Desktop`：檢視既有 archive、搜尋內容，並人工編修 `title.cn`、`author.cn`、`content.cn`。
- `VerseArchiveTranslator Mobile`：在 Android 上延續相同的人工翻譯流程，適合搭配同步資料夾進行手機端編修。

## 快速開始：Windows Release ZIP

1. 到 GitHub Releases 下載最新的 Windows ZIP。
2. 解壓縮到本機資料夾。
3. 執行 `VerseArchiveCurator.exe`。
4. 設定輸出位置與建庫選項，建立 archive JSON。
5. 建庫完成後，執行 `VerseArchiveTranslator.exe` 進行人工翻譯與編修。
6. 如果想在手機上接續編修，可使用 Android 版 Translator，並搭配 Syncthing 等工具同步 `output/` 資料夾。

## 基本使用流程

1. 使用 `VerseArchiveCurator` 建立 archive JSON。
2. 在 `output/` 取得 `english_poems.json`、`philosophy_quotes.json` 等檔案。
3. 使用 `VerseArchiveTranslator Desktop` 或 `VerseArchiveTranslator Mobile` 進行人工翻譯與編修。
4. 翻譯工具主要編修 `title.cn`、`author.cn`、`content.cn`。

## Portable 資料位置

預設情況下，工具會在應用程式旁建立以下資料夾：

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

- `data/`：本機設定
- `logs/`：桌面工具執行日誌
- `output/`：建庫輸出的 archive JSON

## Android 版 Translator

Android 版翻譯器位於 `apps/verse_archive_translator_flutter/`，是 `VerseArchiveTranslator` 的行動版，適合在手機上做人工翻譯與編修。

詳細使用方式請參考：

- `apps/verse_archive_translator_flutter/README.md`

## 開發者資訊

### Python 開發安裝

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

### CLI 入口

- `verse-archive-gui`：啟動 `VerseArchiveCurator`
- `verse-archive-translator`：啟動 `VerseArchiveTranslator Desktop`
- `verse-archive`：CLI 入口，用於建庫、統計與路徑診斷

### 驗證

桌面 / Python：

```bash
python -m pytest
```

Flutter Android，請在 `apps/verse_archive_translator_flutter` 目錄下執行：

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

### 打包

建立 Windows Release 版：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

建立 Debug 版：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

Windows 桌面打包的主要輸出名稱為：

- `VerseArchiveCurator`
- `VerseArchiveTranslator`

## 相關文件

- Android 版說明：`apps/verse_archive_translator_flutter/README.md`
- 桌面翻譯器分析：`docs/analysis/verse_archive_translator_desktop_analysis.md`
- Android 架構說明：`docs/architecture/flutter-android-verse-archive-translator.md`
- Android 相容性說明：`docs/compatibility/verse-archive-translator-mobile-compatibility.md`
- Android Roadmap：`docs/roadmap/flutter-android-verse-archive-translator-roadmap.md`
