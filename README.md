# Verse Archive Toolkit

`Verse Archive Toolkit` 是一套用來抓取、整理、翻譯英文詩與哲思語錄資料的桌面工具。  
一般使用者建議直接下載 GitHub Release 的 ZIP 版本；開發者則可用原始碼安裝。

## 最簡單的使用方式（Release ZIP）

如果你沒有 Python 基礎，直接用這個方式就可以：

1. 到 GitHub 的 Releases 下載最新的 Windows ZIP。
2. 解壓縮到你想放的位置。
3. 開啟資料夾後執行 `VerseArchiveToolkit.exe`。
4. 第一次使用先填入 `ZenQuotes API key`。
5. 設定輸出資料夾。
6. 先把英文詩與哲思語錄目標數量設小一點做測試。
7. 按下「開始建庫」。
8. 建庫完成後，可在主程式按「開啟翻譯工具」，或直接執行 `VerseArchiveTranslator.exe` 進行人工翻譯整理。

不需要另外安裝 Python。  
預設情況下，設定檔、日誌與輸出資料都會放在同一個工具資料夾內，方便備份、搬移與整包刪除。

## 主要功能

- 主程式 GUI：抓取 PoetryDB 英文詩與 ZenQuotes 哲思語錄、調整建庫參數、查看進度與日誌
- 翻譯輔助 GUI：搜尋既有資料、編輯 `title.cn` / `author.cn` / `content.cn`，並保存人工翻譯
- CLI：提供建庫、統計、路徑查詢等常用指令，適合進階使用者或批次流程
- 過濾規則可直接在 GUI 編輯並保存，命中後可設定為 `accept`、`review` 或 `reject`
- 當來源選擇全部時，英文詩與哲思語錄會併行抓取，主畫面可分別查看兩方進度

## Python / 開發安裝

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

如果需要打包：

```bash
python -m pip install -e .[packaging]
```

## 啟動方式

主程式 GUI：

```bash
verse-archive-gui
```

翻譯輔助 GUI：

```bash
verse-archive-translator
```

CLI 入口：

```bash
verse-archive
```

## 資料位置

本工具目前預設採用 portable 方式，資料會放在工具資料夾內：

```text
工具資料夾/
  data/
    settings.json
  logs/
    builder-gui-*.log
    translator-gui-*.log
  output/
    english_poems.json
    philosophy_quotes.json
```

- `data/`：設定檔
- `logs/`：啟動與執行日誌
- `output/`：建庫輸出 JSON

主程式 GUI 的「路徑與診斷」區可直接開啟這些位置，發生問題時也可一鍵複製最近日誌內容。

## 常用 CLI

查看設定檔位置：

```bash
verse-archive settings-path
```

查看日誌資料夾：

```bash
verse-archive logs-path
```

一次查看設定、日誌與輸出位置：

```bash
verse-archive paths
```

執行建庫：

```bash
verse-archive build --source all --poem-target 100 --quote-target 100
```

查看輸出統計：

```bash
verse-archive stats
```

## 測試與打包

執行測試：

```bash
python -m unittest discover -s tests
```

建立 Windows Release 版：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

如果要先排查打包問題，可先改跑 Debug 版：

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

## 隱私與版權提醒

- `ZenQuotes API key` 只保存在本機設定檔，不會提交到 Git 倉庫
- 建議先用少量資料測試，再進行大批量建庫
- 請自行確認 PoetryDB、ZenQuotes 與產出資料的使用限制、署名要求與再散布責任
