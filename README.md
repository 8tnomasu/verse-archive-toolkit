# Verse Archive Toolkit

`Verse Archive Toolkit` 是一套以 Python 製作的桌面與 CLI 工具，目標是幫你建立、過濾、人工翻譯與維護詩作 / 哲思語錄資料庫。

目前專案包含兩個主要桌面 GUI：

- 主程式 GUI：抓取資料、建庫、調整過濾規則、查看進度與摘要
- 翻譯輔助 GUI：搜尋既有 JSON 資料、編輯 `title.cn` / `author.cn` / `content.cn`、保存人工翻譯

同時也保留第一階段整理好的 CLI 與核心模組，方便自動化或批次處理。

## 主要功能

- 使用 `PySide6` 提供正式桌面 GUI，而不是 Web 介面
- PoetryDB / ZenQuotes 抓取流程可在背景執行，不阻塞 GUI
- 過濾規則已從寫死常數重構為可編輯、可保存、可還原預設值的設定模型
- 過濾規則支援 `accept` / `review` / `reject` 三種處理方式
- 本機設定使用 `platformdirs` 存放於使用者設定目錄，不寫入 Git
- 翻譯工具支援全文搜尋、未保存變更提示、上一筆 / 下一筆、隨機抽取未翻譯項目
- CLI 仍可使用 `build`、`stats`、`gui`、`translator`、`settings-path`

## 安裝

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

如果要準備打包：

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

列出本機設定檔位置：

```bash
verse-archive settings-path
```

## 主程式 GUI 說明

主程式 GUI 用於建立資料庫，包含以下能力：

- 輸入並保存 ZenQuotes API key
- 選擇輸出資料夾
- 設定 poem / quote target、batch size、request interval、auto save every、timeout、retries
- 啟動背景抓取與建庫
- 中途取消
- 顯示 accepted / review / rejected / skipped / processed 統計
- 顯示日誌與完成摘要
- 開啟翻譯輔助 GUI

### API key 顯示與保存

- API key 只保存在本機設定檔，不會提交到 Git
- GUI 中以遮罩方式顯示，不會完整印到日誌
- 若 CLI 另外傳入 `--zenquotes-api-key` 或 shell 中設定 `ZENQUOTES_API_KEY`，會優先使用外部提供值

## 翻譯輔助 GUI 說明

翻譯工具面向人工校對與補翻：

- 可搜尋 `author.en`、`title.en`、`content.en`、`content.lines`
- 左側結果列表可快速定位資料
- 右側可編輯 `title.cn`、`author.cn`、`content.cn`
- 保存時會寫回正確 JSON 檔案與欄位
- 詩作的 `content.lines` 不會被破壞
- 若檔案在磁碟上被其他程式改動，保存時會先阻止覆寫
- 切換項目前若有未保存修改，會要求你選擇保存 / 捨棄 / 取消
- 可隨機抽取：
  - 全部資料
  - 只抽英文詩
  - 只抽哲學句
  - 只抽完全未翻譯
  - 只抽部分未翻譯

## 過濾規則設定

主程式 GUI 的 `Filter Rules` 頁籤會直接影響實際 builder 流程。設定內容包含：

- Quotes filters
  - 文字長度範圍
  - phrase blacklist
  - soup-word blacklist
  - philosophy hints
  - 驚嘆號限制
- Poetry filters
  - 行數範圍
  - 全文字數範圍
  - 平均每行長度下限
  - 唯一行比例下限
  - title / author / content 關鍵字排除

每個規則群組都可：

- 啟用 / 停用
- 選擇 `accept` / `review` / `reject`
- 編輯數值與關鍵字清單
- 一鍵還原預設值

### 0 代表不設限

GUI 與實作目前對下列類型支援 `0 = 不設限`：

- 最小值
- 最大值
- 行數上下限
- 長度上下限
- 驚嘆號上限
- 最低平均長度
- 最低唯一行比例

也就是說，如果某個最小 / 最大型規則填 `0`，builder 會把該方向視為不限制。

## 設定檔位置

本機設定檔不放在 repo 中，而是放在使用者設定目錄。

Windows 預設位置通常會是：

```text
%APPDATA%\8tnomasu\Verse Archive Toolkit\settings.json
```

設定內容包含：

- 儲存的 ZenQuotes API key
- 上次使用的輸出資料夾與建庫參數
- GUI 可編輯的 filter settings
- 翻譯工具上次使用的資料夾

若設定檔損毀，程式會回退到預設值，並保留一份 `.corrupt-時間戳記.json` 備份。

## 輸出資料

預設輸出資料夾為：

```text
output/
```

會產生的主要檔案為：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

`accept` 會寫入正式資料，`review` 會寫入待審資料，`reject` 只計入統計，不額外輸出檔案。

## 打包成 Windows EXE

專案已補上基本 PyInstaller 準備：

- GUI 入口：
  - `src/verse_archive_toolkit/gui/builder_app.py`
  - `src/verse_archive_toolkit/gui/translator_app.py`
- 打包腳本：
  - `packaging/build-windows.ps1`
- 基本 spec：
  - `packaging/verse_archive_toolkit_gui.spec`

直接打包範例：

```bash
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows.ps1
```

或只打主程式 GUI：

```bash
python -m PyInstaller --clean --noconsole --name VerseArchiveToolkit --paths src --collect-all PySide6 src/verse_archive_toolkit/gui/builder_app.py
```

打包後：

- `dist/` 內會出現 exe
- 設定檔仍然會寫到使用者設定目錄，不會寫回 repo
- 輸出 JSON 仍依 GUI / CLI 內設定的輸出資料夾保存

目前尚未放入自訂 icon；若之後加入 icon / assets，請同步更新 PyInstaller 指令或 spec。

## 隱私與安全提醒

- 不要把真實 API key 寫進 `.env.example`、README 或任何 tracked 檔案
- 不要把本機設定檔提交到 Git
- 不要把大量抓取結果、暫存檔、build / dist / logs 提交到 repo
- 翻譯工具保存前會檢查檔案是否被其他程式改過，避免誤覆蓋

## 資料來源、版權與再散布提醒

- PoetryDB、ZenQuotes 與其上游內容各自可能有不同授權或使用限制
- 請自行確認原始資料來源、作者著作權、API 條款與再散布條件
- 專案提供的是整理工具與工作流程，不等於自動取得任意文本的再發布權

## 測試與驗證

目前專案內建的驗證重點包含：

- 核心 filter 規則判定
- settings save / load / 損毀容錯
- translation repository 搜尋與保存
- GUI smoke test（離屏啟動主窗與翻譯窗）

執行方式：

```bash
python -m unittest discover -s tests
```

## Repo 備註

- `data/` 目錄中的大型 JSON 仍可保留在本機，但不再由 Git 追蹤
- CLI 與桌面 GUI 共用同一套核心 builder / filter / settings 結構
- 若要驗證 live API 抓取，請自行提供有效 ZenQuotes API key 後再從 GUI 或 CLI 執行建庫
