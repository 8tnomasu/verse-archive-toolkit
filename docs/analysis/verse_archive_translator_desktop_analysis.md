# VerseArchiveTranslator 桌面版分析與行動版映射

本文件以目前 repository 內的桌面版實作為唯一主要依據，整理 VerseArchiveTranslator 的既有行為，並說明 Flutter Android 版如何映射。

## 1. 目前有哪些功能

桌面版核心功能實作位於：

- `src/verse_archive_toolkit/translator.py`
- `src/verse_archive_toolkit/gui/translator_app.py`

目前功能包含：

- 開啟工作目錄
- 載入 archive JSON
- 搜尋 author/title/content
- 以 type filter 篩選清單
- 依 translation state 隨機挑選一筆
- 顯示原文與可編輯譯文
- 保存 `title.cn`、`author.cn`、`content.cn`
- 顯示 translated / partial / untranslated 統計
- 未儲存修改提醒
- 檔案變更衝突檢查

## 2. 操作流程

桌面版 UI 流程在 `src/verse_archive_toolkit/gui/translator_app.py`：

1. 啟動時讀取 `SettingsStore`
2. 解析 `settings.translation.data_dir`
3. 以 `TranslationRepository.load()` 載入資料
4. 搜尋欄與 type combo 控制可見清單
5. random state combo 只影響隨機挑選
6. 點選一筆後載入原文與中文草稿
7. 編輯後標記 dirty
8. 保存時呼叫 `TranslationRepository.save_translation()`

## 3. 資料夾 / 檔案結構

標準檔名在 `src/verse_archive_toolkit/translator.py`：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

行為：

- 若上述標準檔存在，優先只載入標準檔
- 否則載入目前目錄下所有 `*.json`
- 空 JSON list 會被略過

## 4. 設定格式與設定概念

設定型別在 `src/verse_archive_toolkit/settings.py`，保存實作在 `src/verse_archive_toolkit/settings_store.py`。

VerseArchiveTranslator 直接依賴的設定概念主要是：

- `translation.data_dir`

桌面版 path 解析在 `src/verse_archive_toolkit/app_paths.py`：

- 空值時回退到 app root 下的 `output/`
- 相對路徑相對於 application root
- 絕對路徑直接 resolve

## 5. 輸入 / 輸出格式

桌面版資料模型與輔助函式在：

- `src/verse_archive_toolkit/translator.py`
- `src/verse_archive_toolkit/records.py`

常見 schema：

- `type`
- `title.en`
- `title.cn`
- `author.en`
- `author.cn`
- `content.lines`
- `content.en`
- `content.cn`

review 檔常見額外 metadata：

- `reason`
- `filter_detail`
- `source_tag`

桌面版保存行為：

- deep copy 原 record
- 只更新 `title.cn`
- 只更新 `author.cn`
- 只更新 `content.cn`
- 其他 metadata 與 `content.lines` 必須保留

## 6. 桌面 UI 專屬假設

桌面版有以下 UI 假設，不適合直接搬到手機：

- master/detail 雙欄佈局
- `QFileDialog.getExistingDirectory()` 直接選取檔案系統目錄
- 鍵盤導向操作與前後筆按鈕
- 視窗尺寸足以同時展示清單與編輯器

## 7. 哪些部分可直接搬到手機，哪些需要調整

可直接保留的部分：

- JSON schema
- translation state 判定
- 搜尋語意
- random pick 語意
- 保存時只更新中文欄位
- mtime 與 signature 衝突檢查
- 標準檔優先 / `*.json` 回退規則

需要改成手機友善互動的部分：

- 目錄選取改用 Android SAF
- recent workspace 保存為 tree URI bookmark
- 版面改成清單 / 編輯器分頁或窄螢幕切換

## 8. 程式入口、主要模組、關鍵資料模型、關鍵讀寫邏輯

桌面版入口與關鍵檔案：

- 入口 UI: `src/verse_archive_toolkit/gui/translator_app.py`
- repository / 模型: `src/verse_archive_toolkit/translator.py`
- record 工具: `src/verse_archive_toolkit/records.py`
- 設定模型: `src/verse_archive_toolkit/settings.py`
- 設定讀寫: `src/verse_archive_toolkit/settings_store.py`
- path 解析: `src/verse_archive_toolkit/app_paths.py`

## Flutter Android 版映射

目前 Flutter 對應如下：

- UI: `apps/verse_archive_translator_flutter/lib/src/ui/home_page.dart`
- controller: `apps/verse_archive_translator_flutter/lib/src/controllers/translator_controller.dart`
- repository: `apps/verse_archive_translator_flutter/lib/src/services/archive_repository.dart`
- models: `apps/verse_archive_translator_flutter/lib/src/models/archive_models.dart`
- settings 保存: `apps/verse_archive_translator_flutter/lib/src/services/preferences_store.dart`
- Android SAF bridge:
  - `apps/verse_archive_translator_flutter/lib/src/storage/workspace_storage.dart`
  - `apps/verse_archive_translator_flutter/android/app/src/main/kotlin/com/versearchive/verse_archive_translator_flutter/MainActivity.kt`

## 本次嚴格驗收後確認的映射重點

- visible list 只吃 search + type filter
- translation filter 只影響 random pick
- 空 JSON list 會跳過，與桌面版 `if not records: continue` 一致
- 保存時先檢查檔案時間戳，再檢查 signature，再只寫入中文欄位
- `content.lines` 與 review metadata 不會在保存時被覆寫
- Android 端 recent workspace 保存的是 `treeUri + archiveRelativePath`
