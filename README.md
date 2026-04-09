# Verse Archive Toolkit

`Verse Archive Toolkit` 是一套以 Python 製作的桌面與 CLI 工具，用來抓取、過濾、建庫、人工翻譯與維護英文詩 / 哲思語錄資料。

目前專案包含兩個正式桌面 GUI，介面已全面繁體中文化：

- 主程式 GUI：抓取資料、建庫、調整過濾規則、查看進度與摘要
- 翻譯輔助 GUI：搜尋既有 JSON、編輯 `title.cn` / `author.cn` / `content.cn`、保存人工翻譯

同時保留 CLI 與核心模組，方便批次工作、測試與後續擴充。

## 主要功能

- 使用 `PySide6` 提供 Windows 桌面 GUI
- PoetryDB / ZenQuotes 抓取流程採背景執行，不阻塞 GUI
- 當建庫來源選擇 `all` 時，英文詩與哲思語錄會真正併行抓取
- 過濾規則可在 GUI 直接編輯、保存、還原預設值
- 過濾規則支援 `accept` / `review` / `reject`
- 本機設定與日誌使用 `platformdirs` 存放在使用者目錄，並以 `Verse Archive Toolkit` 作為資料夾主體，不寫入 Git
- 啟動時若發生例外，會寫入本機 log，避免 EXE 靜默失敗
- 翻譯工具支援全文搜尋、上一筆 / 下一筆、未保存變更提示、隨機抽取未翻譯資料
- 主程式 GUI 內建「路徑與診斷」區，可直接查看 / 開啟 / 複製設定檔、日誌與輸出位置
- CLI 仍可使用 `build`、`stats`、`gui`、`translator`、`settings-path`、`logs-path`、`paths`

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

當 `--source all` 時，CLI 也會同時並行抓取英文詩與哲思語錄。

查看輸出統計：

```bash
verse-archive stats
```

查詢本機設定檔位置：

```bash
verse-archive settings-path
```

查詢本機日誌資料夾位置：

```bash
verse-archive logs-path
```

一次查看設定檔 / 日誌 / 輸出位置：

```bash
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
- 顯示進度條、目前狀態、已通過 / 待審 / 已拒絕 / 已略過 / 本次已處理
- 可分別查看英文詩與哲思語錄的進度、狀態與統計
- 顯示建庫日誌與完成摘要
- 內建「路徑與診斷」區，可直接開啟設定檔位置、日誌資料夾、輸出資料夾，或複製診斷資訊
- 可直接開啟翻譯輔助 GUI

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

## 過濾規則說明

主程式 GUI 的「過濾規則」分頁會直接影響建庫流程：

- 哲思語錄規則
  - 語錄字數範圍
  - 黑名單片語
  - 心靈雞湯關鍵字
  - 哲思提示詞
  - 驚嘆號上限
- 英文詩規則
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

## 設定檔、日誌與輸出位置

程式會依作業系統與目前使用者環境，自動把本機設定與日誌放到對應的使用者目錄中；路徑主體固定使用 `Verse Archive Toolkit`，不再帶入開發者個人名稱。

主程式 GUI 的「路徑與診斷」區可直接：

- 查看目前設定檔位置
- 查看目前日誌資料夾位置
- 查看目前輸出資料夾位置
- 開啟上述位置
- 複製路徑或完整診斷資訊

CLI 也可使用：

- `verse-archive settings-path`
- `verse-archive logs-path`
- `verse-archive paths`

### 設定檔

Windows 預設位於：

```text
%APPDATA%\Verse Archive Toolkit\settings.json
```

本機設定檔包含：

- ZenQuotes API 金鑰
- 主程式 GUI 最後一次使用的輸出路徑與建庫參數
- 過濾規則設定
- 翻譯輔助 GUI 最後一次使用的資料目錄

若設定檔損毀，程式會自動回退到預設值，並保留一份 `.corrupt-時間戳.json` 備份。

### 啟動日誌

Windows 預設位於：

```text
%LOCALAPPDATA%\Verse Archive Toolkit\Logs\
```

主程式與翻譯工具都會各自建立啟動 log，例如：

```text
builder-gui-20260409-153000.log
translator-gui-20260409-153100.log
```

如果 EXE 啟動失敗、雙擊後沒有畫面，請優先檢查這個目錄。

### 輸出資料

若未在 GUI 另外指定，預設會輸出到目前工作目錄下的：

```text
output\
```

常見輸出檔案：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

主程式 GUI 會以目前設定中的「輸出資料夾」為準，並在「路徑與診斷」區顯示實際解析後路徑。

若使用 CLI 而未指定 `--output-dir`，則會沿用本機設定中的輸出資料夾；若該設定仍為預設值 `output`，代表實際輸出位置會是目前工作目錄下的 `output/`。

若是只有 EXE 的使用者，建議在主程式 GUI 中明確指定固定輸出資料夾，避免從不同工作目錄啟動時把資料散落到不同位置。

## 併行建庫與進度顯示

- 當建庫來源選擇 `英文詩 + 哲思語錄` 或 CLI 指定 `--source all` 時，PoetryDB 與 ZenQuotes 會真正同時執行
- 兩個來源共用同一組取消訊號；按下「停止 / 取消」後，兩邊都會收到停止要求
- 主程式 GUI 會分開顯示：
  - 英文詩進度
  - 哲思語錄進度
  - 各自的已通過 / 待審 / 已拒絕 / 已略過 / 已處理
- 同時保留全域摘要與整體日誌

## Windows 打包

### 為什麼現在改用新的 GUI 入口

PyInstaller 打包時，必須有明確可執行的 GUI 入口。專案目前已提供：

- `src/verse_archive_toolkit/builder_gui_entry.py`
- `src/verse_archive_toolkit/translator_gui_entry.py`

這兩個入口會：

- 正確建立 `QApplication`
- 啟動主視窗
- 安裝全域例外處理
- 把啟動錯誤寫入本機 log
- 在必要時顯示錯誤對話框

### 推薦做法：先打 Debug，再打 Release

Debug 打包：

```bash
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

Release 打包：

```bash
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

若只想打某一個工具，可加上 `-Target Builder` 或 `-Target Translator`。

### Debug 與 Release 的差異

- Debug
  - 使用 `--console`
  - 便於從 PowerShell 直接啟動與排錯
  - 適合先確認 Qt 插件、路徑與啟動流程
- Release
  - 使用 `--windowed`
  - 適合正式交付
  - 失敗時仍會把例外寫入本機 log，避免完全靜默

### 建議的排錯方式

先打 Debug 版，再從 PowerShell 啟動：

```bash
.\dist\windows\debug\VerseArchiveToolkitDebug\VerseArchiveToolkitDebug.exe --console-log
```

若要看 Qt plugin 額外偵錯資訊：

```bash
.\dist\windows\debug\VerseArchiveToolkitDebug\VerseArchiveToolkitDebug.exe --console-log --debug-qt-plugins
```

正式版輸出路徑：

```text
dist\windows\release\VerseArchiveToolkit\
dist\windows\release\VerseArchiveTranslator\
```

Debug 版輸出路徑：

```text
dist\windows\debug\VerseArchiveToolkitDebug\
dist\windows\debug\VerseArchiveTranslatorDebug\
```

### Spec 檔

專案也提供 PyInstaller spec：

- `packaging/verse_archive_toolkit_gui.spec`
- `packaging/verse_archive_translator_gui.spec`

若需要手動調整 PyInstaller 行為，可直接以 spec 為起點。

## 測試與驗證

執行測試：

```bash
python -m unittest discover -s tests
```

目前測試與驗證重點包含：

- CLI 基本功能
- 路徑工具與本機資料夾命名
- `source=all` 併行建庫聚合邏輯
- 設定檔保存 / 載入 / 損毀容錯
- 翻譯 repository 搜尋與保存
- GUI smoke test
- 主程式 GUI 的來源進度區塊與路徑診斷狀態
- GUI 過濾規則 action 下拉選單回填
- PyInstaller 指令與 Windows Debug / Release 打包流程

## 隱私與安全提醒

- 不要把真實 API 金鑰提交到 Git
- 不要把本機設定檔提交到 Git
- 不要把大量抓取結果、建置產物或 log 提交到 repo
- 建議公開 repo 前再次檢查 `output/`、`dist/`、`build/`、`data/`

## 版權與再散布提醒

- PoetryDB / ZenQuotes 為外部資料來源，請自行確認其使用條款
- 抓取下來的內容不代表可任意重新散布
- 若要公開分享資料集、打包程式或翻譯成果，請先確認來源授權與使用範圍
