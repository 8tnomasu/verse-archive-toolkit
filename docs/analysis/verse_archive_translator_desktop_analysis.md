# VerseArchiveTranslator 桌面版分析

本文件整理 repository 內現有桌面版 `VerseArchiveTranslator` 的實作現況，作為 Flutter Android 版的唯一主要依據。

## 1. 目前有哪些功能

桌面版翻譯工具的核心功能相當聚焦，基本上是一個「本機 JSON 人工翻譯 / 編修器」：

- 開啟指定資料夾作為翻譯資料來源。
- 讀取既有 archive JSON 檔案。
- 搜尋 `author.en`、`title.en`、`content.en`，並額外把 `content.lines` 也納入搜尋。
- 依類型篩選：
  - `english_poem`
  - `philosophy`
- 依翻譯完成度隨機挑選項目：
  - `translated`
  - `partial`
  - `untranslated`
- 顯示原文欄位：
  - `title.en`
  - `author.en`
  - `content.en`
- 編輯譯文欄位：
  - `title.cn`
  - `author.cn`
  - `content.cn`
- 保存單筆 record 的人工翻譯回原始 JSON。
- 統計已翻譯 / 部分翻譯 / 未翻譯數量。
- 未儲存變更保護。
- 檔案異動衝突檢查。

主要檔案：

- `src/verse_archive_toolkit/translator.py`
- `src/verse_archive_toolkit/gui/translator_app.py`

## 2. 操作流程

桌面版典型使用流程如下：

1. 啟動 `verse-archive-translator`。
2. 從 `SettingsStore` 載入 `settings.json`。
3. 讀取 `settings.translation.data_dir`，轉為實際資料夾。
4. 掃描該資料夾內可用的 JSON 檔案。
5. 建立結果列表與統計資訊。
6. 使用者從左側列表挑選一筆資料。
7. 右側顯示原文與目前譯文。
8. 使用者編修 `cn` 欄位。
9. 若切換項目或關閉視窗時仍有未儲存變更，先提示保存 / 放棄 / 取消。
10. 保存時先做檔案時間戳與 record signature 驗證，再寫回整份 JSON。
11. 重新載入該檔案，刷新列表與統計。

## 3. 資料夾 / 檔案結構

桌面版預設採 portable 結構，主要路徑定義在 `src/verse_archive_toolkit/app_paths.py`：

```text
<app-root>/
  data/
    settings.json
  logs/
  output/
    english_poems.json
    english_poems_review.json
    philosophy_quotes.json
    philosophy_quotes_review.json
```

翻譯工具實際操作的，是 `translation.data_dir` 指向的資料夾。預設通常是 `output/`。

翻譯工具優先尋找以下四個標準檔名：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

如果這四個都不存在，才退回到「該資料夾底下所有 `*.json`」。

對應程式：

- `translator.py` 的 `STANDARD_ARCHIVE_FILES`
- `app_paths.py` 的 `resolve_output_directory`
- `settings.py` 的 `TranslationSettings.data_dir`

## 4. 設定格式與設定概念

桌面版設定透過 `SettingsStore` 存在 `data/settings.json`，格式由 `AppSettings` 定義：

```json
{
  "schema_version": 2,
  "zenquotes_api_key": "...",
  "build": {
    "output_dir": "output",
    "...": "..."
  },
  "filters": {
    "...": "..."
  },
  "translation": {
    "data_dir": "output"
  }
}
```

對翻譯工具直接相關的只有：

- `translation.data_dir`

概念上它代表「翻譯資料根目錄」。桌面版允許：

- 相對於 app root 的相對路徑
- 絕對路徑

## 5. 輸入 / 輸出格式

資料模型主要由 `records.py` 建立，翻譯工具只編修既有格式，不重新設計 schema。

### 英文詩 record

```json
{
  "type": "english_poem",
  "title": { "en": "Night River", "cn": "" },
  "author": { "en": "Jane Doe", "cn": "" },
  "content": {
    "lines": ["One line", "Two line"],
    "en": "One line\nTwo line",
    "cn": ""
  }
}
```

### 哲思語錄 record

```json
{
  "type": "philosophy",
  "title": { "en": "", "cn": "" },
  "author": { "en": "Laozi", "cn": "" },
  "content": {
    "lines": ["Silence teaches."],
    "en": "Silence teaches.",
    "cn": ""
  }
}
```

### review 檔額外欄位

builder 會在 review 檔加入額外 metadata，翻譯工具不會移除它們，例如：

- `reason`
- `filter_detail`
- `source_tag`

桌面版保存時只更新：

- `title.cn`
- `author.cn`
- `content.cn`

其他欄位與 `content.lines` 都必須保留。

## 6. 桌面 UI 專屬假設

桌面版 `translator_app.py` 內建下列桌面假設：

- 使用 `QFileDialog.getExistingDirectory()` 取得傳統資料夾路徑。
- 以左右分欄 `QSplitter` 呈現 master/detail。
- 視窗可同時顯示完整列表與完整編輯區。
- 關閉視窗時用 `closeEvent()` 處理未儲存確認。
- 路徑可直接表示為本機絕對或相對 filesystem path。

這些假設在 Android 上都不能直接照搬。

## 7. 哪些部分可直接搬到手機，哪些需要手機友善調整

### 可直接搬移的核心邏輯

- 標準檔名與 fallback 掃描邏輯
- record schema
- `translated / partial / untranslated` 判定規則
- 搜尋欄位
- 類型分類
- 保存時只更新 `cn` 欄位
- 保存前的衝突檢查概念
- 寫回整份 JSON 的策略

### 需要改成手機友善互動的部分

- 傳統資料夾路徑改為 Android Storage Access Framework
- `QFileDialog` 改為 `ACTION_OPEN_DOCUMENT_TREE`
- 左右雙欄改為：
  - 大螢幕雙欄
  - 手機單欄列表 / 編修切換
- 關閉視窗改為 `PopScope`
- 最近目錄改存為 persisted tree URI，而不是 filesystem path

## 8. 程式入口、主要模組、關鍵資料模型、關鍵讀寫邏輯位置

### 程式入口

- `src/verse_archive_toolkit/translator_gui_entry.py`

### 主要 GUI 模組

- `src/verse_archive_toolkit/gui/translator_app.py`

### 關鍵資料模型 / 邏輯

- `src/verse_archive_toolkit/translator.py`
  - `ArchiveDocument`
  - `ArchiveEntry`
  - `translation_state()`
  - `TranslationRepository.load()`
  - `TranslationRepository.search()`
  - `TranslationRepository.stats()`
  - `TranslationRepository.random_entry()`
  - `TranslationRepository.save_translation()`

- `src/verse_archive_toolkit/records.py`
  - `get_nested()`
  - `get_lines()`
  - `build_poem_record()`
  - `build_quote_record()`

- `src/verse_archive_toolkit/storage.py`
  - `load_json_list()`
  - `write_json()`

- `src/verse_archive_toolkit/settings.py`
  - `TranslationSettings`
  - `AppSettings`

- `src/verse_archive_toolkit/settings_store.py`
  - `SettingsStore.load()`
  - `SettingsStore.save()`

- `src/verse_archive_toolkit/app_paths.py`
  - `resolve_output_directory()`
  - `serialize_app_relative_path()`

## 行動版映射摘要

Flutter Android 版應保留以下桌面版不變點：

- JSON schema 不變
- 搜尋語意不變
- 翻譯狀態判定不變
- 單筆保存語意不變
- review metadata 保留不變
- `content.lines` 保留不變

Flutter Android 版允許調整的點：

- 路徑表示法從 path 改為 persisted tree URI + 相對路徑
- 互動從桌面分欄改為手機優先的列表 / 編修切換
- 設定儲存位置改為 app-private preferences
- 但若使用者選到 portable 根目錄，仍會讀取桌面版 `data/settings.json` 的 `translation.data_dir`
