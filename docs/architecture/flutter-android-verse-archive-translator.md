# Flutter Android 版架構說明

## 目標

Flutter Android 版的設計目標不是重新發明 VerseArchiveTranslator，而是把桌面版的核心翻譯流程搬到 Android，同時適配：

- Android Storage Access Framework
- persisted URI permission
- Syncthing 同步資料夾
- 手機螢幕尺寸與長時間人工編修

## 目錄位置

新 app 位於：

`apps/verse_archive_translator_flutter/`

既有 Python 桌面版程式碼不做破壞性修改。

## 分層

### 1. UI 層

檔案：

- `lib/src/ui/home_page.dart`
- `lib/src/app.dart`

責任：

- 顯示工作目錄狀態
- 顯示搜尋 / 篩選 / 列表
- 顯示原文與譯文編修區
- 顯示未儲存狀態、錯誤與警告
- 在窄螢幕下切換「列表 / 編修」視圖
- 在寬螢幕下提供雙欄模式

### 2. 狀態控制層

檔案：

- `lib/src/controllers/translator_controller.dart`

責任：

- 啟動時載入 app settings
- 開啟 / 重新開啟工作目錄
- 維護最近使用資料夾
- 套用搜尋與篩選
- 維護目前選取項目與譯文 draft
- 判定 dirty state
- 執行保存並刷新畫面資料

### 3. Repository / 業務邏輯層

檔案：

- `lib/src/services/archive_repository.dart`
- `lib/src/models/archive_models.dart`

責任：

- 複製桌面版 JSON 掃描與 entry 邏輯
- 解析桌面版 `data/settings.json`
- 推斷 archive root
- 載入 JSON list
- 建立 `ArchiveDocument` / `ArchiveEntry`
- 複製桌面版 `translated / partial / untranslated` 規則
- 搜尋與隨機挑選
- 保存時只更新 `cn` 欄位並保留 metadata
- 保存前做檔案衝突檢查

## Android 檔案存取設計

### 為什麼不用傳統 path

Android 11+ 之後，對共用儲存空間的直接路徑存取限制很大。Syncthing 同步到手機的資料夾，若要讓 App 長期可重開、可寫入、可重新瀏覽，最穩定的做法是：

- `ACTION_OPEN_DOCUMENT_TREE`
- `takePersistableUriPermission`
- 之後透過 `DocumentFile` / `ContentResolver` 存取

### 目前做法

檔案：

- `android/app/src/main/kotlin/com/versearchive/verse_archive_translator_flutter/MainActivity.kt`
- `lib/src/storage/workspace_storage.dart`

做法：

1. Flutter 端呼叫 `MethodChannel`
2. Android 端打開資料夾選取器
3. 取得 tree URI
4. 保存 persisted URI permission
5. Flutter 端只記住：
   - `treeUri`
   - `displayName`
   - `archiveRelativePath`
6. 後續所有檔案列舉 / 讀取 / 寫入都透過：
   - `listDirectory`
   - `readTextFile`
   - `writeTextFileIfUnchanged`

### 工作目錄解析策略

選到一個資料夾後，repository 會依序判斷：

1. 若 `data/settings.json` 存在，且 `translation.data_dir` 為可在 tree 內解析的相對路徑，就優先用它
2. 否則若所選資料夾本身就有 archive JSON，直接使用
3. 否則若存在 `output/` 且裡面有 archive JSON，改用 `output/`
4. 否則報錯

這樣同時支援：

- 直接選 output 目錄
- 選 portable toolkit 根目錄

## 資料模型對應

### Flutter 端主要 model

- `DirectoryItem`
- `ArchiveDocument`
- `ArchiveEntry`
- `WorkspaceBookmark`
- `ResolvedArchiveDirectory`
- `TranslatorAppSettings`

### 與桌面版對應

桌面版對應：

- `ArchiveDocument` -> Flutter `ArchiveDocument`
- `ArchiveEntry` -> Flutter `ArchiveEntry`
- `translation_state()` -> Flutter `translationState()`
- `TranslationRepository.search()` -> Flutter `filterEntries()`
- `TranslationRepository.save_translation()` -> Flutter `ArchiveRepository.saveTranslation()`

## 保存策略

桌面版保存策略：

1. 檢查檔案 mtime
2. 檢查當前 record signature
3. 更新 `title.cn` / `author.cn` / `content.cn`
4. 整份 JSON 重寫

Flutter 版保留相同精神：

1. 重新讀取目前檔案
2. 若 `lastModified` 已變，檢查當前 record signature 是否仍與使用者打開時相同
3. 若不同，阻止保存並要求重新載入
4. 若相同，保留其他 record 與 metadata 不變，只更新當前 record 的 `cn` 欄位
5. 呼叫 `writeTextFileIfUnchanged()`，再次以 `expectedLastModified` 防止最後一瞬間競態覆寫

## 設定儲存

### Android 版 app settings

檔案：

- `lib/src/services/preferences_store.dart`

目前保存在 app-private `SharedPreferences`。

內容包括：

- 最近使用工作目錄列表
- 最近一次成功打開的 workspace bookmark

### 與桌面版的關係

Android 版不會改寫桌面版 `data/settings.json`，避免把 Android 專屬 URI 設定寫進桌面 portable config。

但是：

- 若使用者選到 portable 根目錄
- 且存在桌面版 `data/settings.json`

Android 版會讀取其中的 `translation.data_dir` 概念來定位實際 archive root。

## UI 佈局策略

### 手機

- 上方工作目錄資訊
- 中間列表或編修區
- 底部 `NavigationBar` 切換：
  - 列表
  - 編修

### 大螢幕 / 平板

- 左側列表
- 右側編修區

## 驗證策略

目前至少做到：

- `flutter analyze` 通過
- `flutter test` 通過
- `flutter build apk --debug` 成功

測試檔：

- `test/archive_repository_test.dart`

重點覆蓋：

- 從桌面版 `settings.json` 解析 archive root
- 保存翻譯時保留 `content.lines`

## 目前已知取捨

- 目前以單筆保存為主，沒有額外做草稿自動保存
- 沒有做複雜的多檔批次編修
- 沒有實作背景監看外部檔案變化，只在保存與重載時檢查衝突
- 設定使用 SharedPreferences，沒有嘗試和桌面版共用同一份 settings 檔

這些取捨都是為了先交付一個最小但可編譯、可執行、可實際保存的 Android 初版
