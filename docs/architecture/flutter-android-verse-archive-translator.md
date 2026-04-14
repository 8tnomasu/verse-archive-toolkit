# Flutter Android VerseArchiveTranslator 架構說明

## 目標

這個 Flutter App 的架構目標不是重新設計產品，而是把桌面版 VerseArchiveTranslator 的核心語意拆成適合 Android 的最小可用層次：

- UI 顯示與互動
- controller 管理狀態與流程
- repository 管理桌面版相容邏輯
- storage bridge 管理 Android SAF 檔案 IO

## 目錄結構

App 專案位於：

- `apps/verse_archive_translator_flutter/`

主要程式碼：

- `lib/main.dart`
- `lib/src/app.dart`
- `lib/src/ui/home_page.dart`
- `lib/src/controllers/translator_controller.dart`
- `lib/src/services/archive_repository.dart`
- `lib/src/services/preferences_store.dart`
- `lib/src/models/archive_models.dart`
- `lib/src/storage/workspace_storage.dart`
- `android/app/src/main/kotlin/com/versearchive/verse_archive_translator_flutter/MainActivity.kt`

## 分層

### UI

`home_page.dart` 負責：

- 顯示 workspace 狀態
- 顯示搜尋與 type filter
- 顯示 translation filter for random pick
- 顯示 entry list
- 顯示原文 / 譯文編輯區
- 顯示 warnings、error、info 與 dirty state

### Controller

`translator_controller.dart` 負責：

- App 啟動時恢復 recent workspace
- 開啟 / 重新載入 workspace
- 維護可見清單與選取 entry
- 維護 draft 欄位
- 判定未儲存狀態
- 呼叫 repository 保存

關鍵語意：

- visible list = search + type filter
- translation filter = random pick only

### Repository

`archive_repository.dart` 負責與桌面版對齊的領域邏輯：

- 解析 archive root
- 載入標準 JSON 檔
- 空 JSON list 跳過
- record / document 轉換
- 保存時只更新 `cn` 欄位
- 保存前做 mtime / signature 衝突檢查

### Storage

`workspace_storage.dart` 定義 Flutter 端抽象。

`MainActivity.kt` 提供 Android 實作：

- `pickWorkspace`
- `listDirectory`
- `readTextFile`
- `writeTextFileIfUnchanged`

這一層不理解 VerseArchiveTranslator schema，只處理 URI tree 內的安全檔案操作。

### Preferences

`preferences_store.dart` 使用 `SharedPreferences` 保存：

- recent workspace bookmarks
- `treeUri`
- `displayName`
- `archiveRelativePath`
- `resolutionSource`
- `lastOpenedAt`

## 資料流

1. App 啟動
2. `PreferencesStore.load()`
3. `TranslatorController.initialize()`
4. 若存在上次 workspace，controller 呼叫 repository 重新解析與載入
5. repository 透過 storage bridge 讀取 SAF tree 內 JSON
6. models 轉成 `ArchiveDocument` / `ArchiveEntry`
7. UI 綁定 controller 顯示內容
8. 保存時 controller 將 draft 傳給 repository
9. repository 檢查檔案未變更後寫回 JSON

## 與桌面版對齊的重點決策

### 1. translation state

沿用桌面版 `translation_state()`：

- 只把 `title.en`
- `author.en`
- `content.en`

視為 required fields。

`content.lines` 只用於顯示與搜尋 fallback，不參與翻譯完成判定。

### 2. 搜尋與 random pick

沿用桌面版 UI 語意：

- 搜尋結果由 search query + type filter 決定
- translation filter 只作用在 random pick

### 3. 保存策略

沿用桌面版 `save_translation()`：

- 先檢查 mtime
- 再檢查 signature
- deep copy record
- 只更新 `title.cn`
- 只更新 `author.cn`
- 只更新 `content.cn`

### 4. archive root 解析

Android 版依序嘗試：

1. `data/settings.json` 的 `translation.data_dir`
2. 使用者目前選取的 tree 根目錄
3. `output/`

這對齊桌面版 portable workflow，但保留 Android SAF 不能跳出已授權 tree 的限制。

## 測試策略

目前測試集中在單元層：

- model 相容性測試
- repository 保存與衝突測試
- preferences round-trip 測試
- controller restore / dirty state / random filter 測試

尚未加入的測試：

- 真機或 emulator 上的 SAF instrumentation test
- 大型資料集效能測試
