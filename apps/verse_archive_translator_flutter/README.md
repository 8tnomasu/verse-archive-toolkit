# VerseArchiveTranslator Mobile

`VerseArchiveTranslator Mobile` 是 `VerseArchiveToolkit` 內的 Android 翻譯工具，用於在手機上進行 verse archive JSON 的人工翻譯與編修。

## 這是什麼？

`VerseArchiveTranslator Mobile` 是 `VerseArchiveTranslator` 的 Flutter Android 版本，延續桌面版的人工翻譯工作流程，並針對手機操作方式重新整理介面。

這個 App 主要用於：

- 在 Android 上開啟本機或同步資料夾中的 archive JSON
- 檢視現有 archive 內容並進行人工翻譯
- 編修 `title.cn`、`author.cn`、`content.cn`
- 維持與桌面版一致的搜尋、儲存與隨機抽取語意

一般使用情境是先在桌面端用 `VerseArchiveCurator` 建立 archive JSON，再透過同步資料夾將 `output/` 帶到 Android 上，使用 `VerseArchiveTranslator Mobile` 進行人工翻譯與編修。

## 名稱說明

- `VerseArchiveToolkit`：整個 repository 與工具集合名稱
- `VerseArchiveTranslator Mobile`：Android 版人工翻譯與編修工具
- `VerseArchiveTranslator Desktop`：桌面端人工翻譯與編修工具

## 這個 App 提供什麼？

- Android 優先的 Flutter 介面
- 透過 Android Storage Access Framework 存取本機資料夾
- 直接讀寫與桌面版相容的 archive JSON
- 人工編修翻譯欄位 `title.cn`、`author.cn`、`content.cn`
- 與桌面版一致的搜尋、儲存、隨機抽取與翻譯狀態判定

## 快速開始：Android 使用方式

1. 在桌面端先用 `VerseArchiveCurator` 建立 archive JSON。
2. 將 `output/` 資料夾同步到 Android，常見做法是透過 Syncthing。
3. 在 Android 安裝 `VerseArchiveTranslator Mobile`。
4. 開啟 App 後選擇同步完成的工作目錄或 portable `VerseArchiveToolkit` 根目錄。
5. 在 `List` 分頁搜尋或篩選要翻譯的內容。
6. 在 `Edit` 分頁編修 `title.cn`、`author.cn`、`content.cn`，再儲存變更。

## 基本使用流程

1. App 載入 archive 目錄中的 JSON 檔案。
2. 你可以在列表中搜尋、依類型篩選，或用隨機抽取功能挑選內容。
3. 進入編修畫面後，可檢視原文並編輯中文欄位。
4. App 只會編修翻譯欄位，不改動既有英文內容與桌面版相容格式。

## 目前介面結構

手機版介面以緊湊且高頻操作優先為原則，主要保留兩個分頁：

- `List`：搜尋、篩選、查看列表與抽取內容
- `Edit`：檢視原文、編輯譯文與儲存

### List 分頁

`List` 分頁主要提供：

- 搜尋欄位
- 類型篩選
- 隨機抽取範圍篩選
- 可見結果摘要
- 結果列表

可見結果摘要只根據目前列表中可見的內容計算：

- `search query` 與 `type filter` 會影響可見結果
- translated / partial / untranslated 統計以可見結果為準
- `translation filter` 不影響可見列表與可見摘要
- `translation filter` 只影響隨機抽取

### Edit 分頁

`Edit` 分頁聚焦在人工翻譯工作本身，主要包含：

- 精簡的記錄標頭
- 原文區塊
- 翻譯區塊
- 可展開的 metadata 區塊
- 低高度的同步 / 儲存操作列

原文卡片與翻譯卡片都支援長按複製純文字內容，方便在手機端快速整理與編修。

## 工作區與資料夾

這個 App 可直接處理與桌面版相容的 archive JSON，常見資料來源包括：

- 同步到 Android 的 `output/` 資料夾
- portable `VerseArchiveToolkit` 根目錄下的 `output/`
- 已授權給 Android Storage Access Framework 的本機資料夾

App 會記住最近使用過的工作區，方便下次快速開啟。

## 鍵盤與版面配置

為了避免手機輸入時出現畫面溢出或被鍵盤遮住，版面目前採用以下策略：

- `Scaffold.resizeToAvoidBottomInset`
- 可捲動的編輯內容區
- 翻譯欄位聚焦時使用 `Scrollable.ensureVisible`
- 編輯區底部保留額外 padding
- 鍵盤開啟時隱藏底部導覽列

這些設計可避免先前固定底部區塊造成的 `BOTTOM OVERFLOWED BY 76 PIXELS` 問題。

## 開發者資訊

### Flutter 開發與執行

請在 `apps/verse_archive_translator_flutter` 目錄下執行：

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

### 驗證

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

### 打包

建立 Debug APK：

```bash
flutter build apk --debug
```

建立 Release APK：

```bash
flutter build apk --release
```

常見輸出位置：

- Debug APK：`build/app/outputs/flutter-apk/app-debug.apk`
- Release APK：`build/app/outputs/flutter-apk/app-release.apk`

## 相關文件

- 專案首頁：`README.md`
- 桌面翻譯器分析：`docs/analysis/verse_archive_translator_desktop_analysis.md`
- Android 架構說明：`docs/architecture/flutter-android-verse-archive-translator.md`
- Android 相容性說明：`docs/compatibility/verse-archive-translator-mobile-compatibility.md`
- Android Roadmap：`docs/roadmap/flutter-android-verse-archive-translator-roadmap.md`
