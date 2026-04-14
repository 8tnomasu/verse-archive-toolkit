# VerseArchiveTranslator Flutter Android App

這個目錄提供 `VerseArchiveTranslator` 的 Flutter Android 初版，目標不是另做一套翻譯平台，而是把桌面版的人工翻譯與人工編修流程搬到手機上，並維持既有 JSON 資料、設定概念與輸出相容。

## 目前已完成

- 以 Android Storage Access Framework 選取 Syncthing 同步下來的工作目錄
- 取得並保存 persisted URI permission
- 保存 recent workspaces，重開 App 後自動恢復上次工作目錄
- 依桌面版語意解析 archive root
  - 先讀 `data/settings.json` 的 `translation.data_dir`
  - 找不到時回退到目前選取目錄
  - 再回退到 `output/`
- 載入標準 archive JSON
  - `english_poems.json`
  - `english_poems_review.json`
  - `philosophy_quotes.json`
  - `philosophy_quotes_review.json`
- 若標準檔不存在，回退載入目前目錄下的 `*.json`
- 略過空 JSON list，行為與桌面版一致
- 搜尋 author/title/content 與 `content.lines`
- 以 type filter 篩選清單
- 以 translation filter 控制隨機挑選範圍
  - 這個 filter 不影響目前清單，與桌面版一致
- 顯示原文、譯文、翻譯狀態與常見 metadata
- 只更新 `title.cn`、`author.cn`、`content.cn`
- 保留 `content.lines` 與其他 metadata，不覆寫 review 欄位
- 保存前檢查檔案時間戳與 record signature，避免寫壞同步中的檔案
- 顯示未儲存狀態

## 桌面版對應

核心對照來源：

- `src/verse_archive_toolkit/translator.py`
- `src/verse_archive_toolkit/gui/translator_app.py`
- `src/verse_archive_toolkit/records.py`
- `src/verse_archive_toolkit/app_paths.py`
- `src/verse_archive_toolkit/settings.py`
- `src/verse_archive_toolkit/settings_store.py`

目前 Flutter 版已對齊的關鍵語意：

- `translation_state()` 只看 `title.en`、`author.en`、`content.en`
- `content_en` 顯示時可回退到 `content.lines`
- 搜尋會同時搜尋 `content.en` 與 `content.lines`
- random pick 使用 type filter 與 translation filter，但不吃 search query
- 保存時先檢查檔案變更，再檢查 signature，最後只改中文欄位

## Android 檔案存取說明

Android 版不能假設能直接拿到傳統絕對路徑，因此實作採用：

- `ACTION_OPEN_DOCUMENT_TREE`
- `takePersistableUriPermission`
- `DocumentFile`
- `ContentResolver`

App 內部保存的是 `treeUri` 與 archive 相對路徑，不保存絕對檔案系統路徑。

### 與桌面版不同之處

桌面版的 `translation.data_dir` 會交給 `resolve_output_directory()` 做一般路徑解析；Android 版只能在使用者授權的 tree 內相對解析。因此：

- 相對子目錄，例如 `output`，可正常對齊 portable workflow
- `.` 會視為目前 tree 根目錄
- 包含父層跳脫或絕對路徑的設定值無法在 Android SAF 下直接還原

這是平台限制，不是資料格式變更。

## 建置與執行

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
flutter run
```

Debug APK 會輸出到：

- `build/app/outputs/flutter-apk/app-debug.apk`

## 測試重點

目前測試覆蓋：

- archive root 解析
- 空 JSON list 跳過
- 保存時只更新中文欄位並保留 metadata
- mtime / signature 衝突檢查
- translation state 與搜尋語意
- recent workspace bookmark round-trip
- controller 的 workspace restore、dirty state、random filter 語意

## 已知限制

- 目前沒有全文 lazy loading，大型資料集仍是一次載入
- 沒有桌面版的前後筆快捷移動與鍵盤導向操作
- Android 無法直接復用桌面版的絕對路徑型 `translation.data_dir`
- 尚未加入更細的檔案級 merge / diff UI
