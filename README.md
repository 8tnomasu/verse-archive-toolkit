# Verse Archive Toolkit

`Verse Archive Toolkit` 是一套以 Python 製作的桌面與 CLI 工具，用來抓取、過濾、建庫、人工翻譯與維護英文詩 / 哲思語錄資料。

目前專案提供兩個正式桌面 GUI，介面為完整繁體中文：

- 主程式 GUI：抓取資料、建庫、調整過濾規則、查看雙來源進度與摘要
- 翻譯輔助 GUI：搜尋既有 JSON、編輯 `title.cn` / `author.cn` / `content.cn`、保存人工翻譯

同時保留 CLI 與核心模組，方便批次工作、測試與後續擴充。

## 主要功能

- 使用 `PySide6` 提供桌面 GUI
- PoetryDB / ZenQuotes 在 `source=all` 時真正併行抓取
- 主程式 GUI 可分別查看英文詩與哲思語錄的進度、狀態與統計
- 過濾規則可在 GUI 直接編輯、保存、還原預設值
- 過濾規則支援 `accept` / `review` / `reject`
- 主畫面支援垂直捲動，下方執行區固定保留操作、狀態、摘要與日誌
- 按下「開始建庫」後，介面會自動聚焦到下方執行狀態區
- 路徑與診斷區可直接開啟設定檔位置、日誌資料夾、輸出資料夾與最近日誌位置
- 發生問題時可一鍵複製最近日誌內容
- 預設設定檔、日誌與輸出都放在工具資料夾內，偏向 portable / self-contained 使用方式
- 啟動時若發生例外，會寫入本機 log，避免 EXE 完全靜默失敗

## 安裝

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

若要準備 PyInstaller 打包：

```bash
python -m pip install -e .[packaging]
```

## 啟動方式

主程式 GUI：

```bash
verse-archive-gui
```

或：

```bash
verse-archive gui
```

翻譯輔助 GUI：

```bash
verse-archive-translator
```

或：

```bash
verse-archive translator
```

CLI 建庫：

```bash
verse-archive build --source all --poem-target 500 --quote-target 500
```

查看輸出統計：

```bash
verse-archive stats
```

查詢路徑：

```bash
verse-archive settings-path
verse-archive logs-path
verse-archive paths
```

## 主程式 GUI 說明

主程式 GUI 用於建立資料庫，主要功能如下：

- 輸入並保存 `ZenQuotes API 金鑰`
- 設定輸出資料夾
- 設定英文詩目標數量
- 設定哲思句目標數量
- 設定每批抓取筆數
- 設定請求間隔、逾時、最大重試次數
- 設定每幾筆自動儲存
- 查看全域統計與雙來源統計
- 查看即時日誌與完成摘要

### 版面與操作流程

主畫面分成兩個區塊：

- 上方可捲動區：建庫設定、路徑與診斷、翻譯工具入口
- 下方固定執行區：`儲存設定`、`開始建庫`、`停止 / 取消`、`複製最近日誌內容`、執行狀態、雙來源進度、全域摘要、日誌輸出

這樣在建庫期間，大部分操作都可直接在下半部完成，不必再上下來回捲動。

按下「開始建庫」後，主畫面會自動把下方執行區調整到更醒目的高度，讓使用者立刻看到進度、摘要與日誌。

### 路徑與診斷

主程式 GUI 的「路徑與診斷」區可直接：

- 查看設定檔位置
- 查看日誌資料夾位置
- 查看最近啟動日誌位置
- 查看目前輸出資料夾位置
- 開啟上述位置
- 複製最近日誌內容

### API 金鑰保存與遮罩

- API 金鑰只會保存在本機設定檔，不會寫入 Git 倉庫
- GUI 中只顯示遮罩後內容，不會把完整金鑰寫入日誌
- 若使用 CLI，也可以改用 `--zenquotes-api-key` 或環境變數 `ZENQUOTES_API_KEY`

## 翻譯輔助 GUI 說明

翻譯輔助 GUI 用於人工翻譯既有 JSON：

- 可搜尋 `author.en`、`title.en`、`content.en`、`content.lines`
- 可依類型篩選英文詩 / 哲思語錄
- 可查看總筆數、已完成翻譯、部分翻譯、未翻譯
- 可編輯 `title.cn`、`author.cn`、`content.cn`
- 保存時會保留原始 `content.lines`
- 支援上一筆 / 下一筆
- 支援隨機抽取未翻譯、部分翻譯或已完成翻譯資料
- 有未保存變更提示與覆寫保護

若翻譯資料來源仍為工具資料夾內的預設輸出，設定會優先保存成相對路徑，讓整包工具搬移時仍保持可攜。

## 過濾規則

主程式 GUI 的「過濾規則」分頁會直接影響建庫流程。

哲思語錄規則包含：

- 語錄字數範圍
- 黑名單片語
- 心靈雞湯關鍵字
- 哲思提示詞
- 驚嘆號上限

英文詩規則包含：

- 行數範圍
- 全文字數範圍
- 平均每行字數下限
- 唯一行比例下限
- 標題 / 作者 / 內容排除關鍵字

每條規則都可：

- 啟用 / 停用
- 指定命中後 `accept` / `review` / `reject`
- 保存到本機設定檔
- 一鍵還原預設值

### `0 = 不設限`

GUI 中數值型規則都支援 `0 = 不設限`，包含：

- 最小值
- 最大值
- 行數上下限
- 字數上下限
- 驚嘆號上限
- 其他數值門檻

## 預設資料位置

這個工具目前預設採用可攜式資料夾策略。

不論是開發模式還是打包後的 EXE，預設都會把設定檔、日誌與輸出放在「程式資料夾」內，而不是 `%APPDATA%` / `%LOCALAPPDATA%`。

### 預設結構

```text
程式資料夾/
  data/
    settings.json
  logs/
    builder-gui-20260415-120000.log
    translator-gui-20260415-120100.log
  output/
    english_poems.json
    english_poems_review.json
    philosophy_quotes.json
    philosophy_quotes_review.json
```

在開發模式下，這個「程式資料夾」通常就是 repo 根目錄。

在 Windows 打包後，這個「程式資料夾」通常就是 EXE 所在的資料夾，例如：

```text
dist\windows\release\VerseArchiveToolkit\
```

### 這樣做的好處

- 工具更接近 portable / self-contained 使用方式
- 備份、搬移與整包刪除更直觀
- 不會再把資料默默寫進使用者系統資料夾
- release 使用者只看工具資料夾，就能找到設定、日誌與輸出

### CLI 路徑查詢

CLI 會反映相同策略：

- `verse-archive settings-path`
- `verse-archive logs-path`
- `verse-archive paths`

### 路徑覆寫

若真的需要改變工具資料夾根位置，可自行設定環境變數：

```text
VERSE_ARCHIVE_TOOLKIT_HOME
```

未設定時，程式會以目前工具資料夾作為根目錄。

## 併行建庫與進度顯示

- 當建庫來源選擇 `英文詩 + 哲思語錄` 或 CLI 指定 `--source all` 時，PoetryDB 與 ZenQuotes 會真正同時執行
- 兩個來源共用同一組取消訊號；按下「停止 / 取消」後，兩邊都會收到停止要求
- 主程式 GUI 會分開顯示：
  - 英文詩進度
  - 哲思語錄進度
  - 各自的已通過 / 待審 / 已拒絕 / 已略過 / 已處理
- 同時保留全域摘要與整體日誌

## Windows 打包

### GUI 入口

PyInstaller 目前使用兩個明確入口：

- `src/verse_archive_toolkit/builder_gui_entry.py`
- `src/verse_archive_toolkit/translator_gui_entry.py`

這些入口會處理：

- 建立 `QApplication`
- 啟動 GUI 視窗
- 設定例外處理
- 把啟動失敗訊息寫入 `logs/`
- 在必要時顯示錯誤對話框

### Debug 打包

```bash
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

### Release 打包

```bash
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

兩個腳本都支援：

```bash
-Target Builder
-Target Translator
```

### 腳本輸出語言與編碼

為了避免 Windows PowerShell 5.1 出現中文亂碼，打包腳本的主輸出統一使用英文，並在腳本開頭主動設定 UTF-8 console 編碼。

### Debug 與 Release 的差別

- Debug
  - 使用 `--console`
  - 適合先看 traceback、Qt plugin 訊息與 PyInstaller 啟動輸出
- Release
  - 使用 `--windowed`
  - 適合正式交付
  - 若啟動失敗，優先查看工具資料夾內的 `logs/`

### Debug 啟動排錯

```bash
.\dist\windows\debug\VerseArchiveToolkitDebug\VerseArchiveToolkitDebug.exe --console-log
```

若要同時查看 Qt plugin 訊息：

```bash
.\dist\windows\debug\VerseArchiveToolkitDebug\VerseArchiveToolkitDebug.exe --console-log --debug-qt-plugins
```

### 打包後資料位置

打包腳本產生的 GUI 版本，執行時也會把資料寫在該 app 資料夾內的：

- `data/`
- `logs/`
- `output/`

也就是說，release 使用者拿到整包資料夾後，不需要另外去系統目錄找設定或日誌。

## 測試

執行測試：

```bash
python -m unittest discover -s tests
```

目前測試涵蓋重點包括：

- CLI 核心功能
- 雙來源併行建庫
- 過濾規則設定模型
- portable 路徑工具
- 設定檔保存 / 載入 / 損毀回退
- GUI smoke test
- 主程式 GUI 的雙來源進度與固定操作列
- 主程式 GUI 的最近日誌複製功能

## 隱私與安全提醒

- 不要把真實 API 金鑰提交到 Git
- 不要把本機設定檔、log、輸出資料、打包產物提交到 repo
- `.gitignore` 已排除 `data/`、`logs/`、`output/`、`dist/`、`build/`

## 版權與資料再散布提醒

- PoetryDB / ZenQuotes 的來源資料可能各自有授權條件與使用限制
- 建議在公開再散布前，先確認來源資料的使用條款
- 翻譯後資料屬於衍生整理成果，也應自行評估是否適合公開發布
