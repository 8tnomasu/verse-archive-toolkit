# VerseArchiveTranslator Flutter Android App

這個目錄包含 `VerseArchiveTranslator` 的 Flutter Android 初版。

它的定位不是新的翻譯平台，也不是 AI / API 翻譯工具，而是：

- 直接操作本機資料夾
- 編修與保存人工翻譯
- 與桌面版 JSON schema 相容
- 適合搭配 Syncthing 在手機上使用

## 功能範圍

目前已完成：

- 選擇工作資料夾
- 支援 Android Storage Access Framework
- persisted URI permission
- recent workspaces
- 自動解析 portable 根目錄與 `translation.data_dir`
- 載入既有 archive JSON
- 搜尋
- 類型篩選
- 翻譯狀態篩選
- 隨機挑一筆
- 顯示原文
- 編輯 `title.cn` / `author.cn` / `content.cn`
- 保存回原始 JSON
- 未儲存狀態提示
- 保存前衝突檢查
- 載入警告顯示

## 與桌面版的關係

Flutter 版是依照 repository 中現有桌面版實作搬移而來，核心相容原則如下：

- 沿用同一套 JSON schema
- 沿用同一套標準檔名
- 沿用同一套翻譯狀態判定
- 保存時只更新 `cn` 欄位
- 保留 `content.lines` 與 review metadata

詳細分析與相容性說明請參考：

- `../../docs/analysis/verse_archive_translator_desktop_analysis.md`
- `../../docs/compatibility/verse-archive-translator-mobile-compatibility.md`
- `../../docs/architecture/flutter-android-verse-archive-translator.md`

## Android 檔案存取限制與做法

### 為什麼不用傳統路徑

Android 對共用儲存空間的路徑式存取限制很多，尤其是使用者自己選到的 Syncthing 同步資料夾。

若要讓 app：

- 可以重新打開先前選過的資料夾
- 可以在重啟 app 後仍然讀寫
- 不依賴寬鬆的 legacy storage 權限

最穩定的方式是：

- `ACTION_OPEN_DOCUMENT_TREE`
- `takePersistableUriPermission`
- `DocumentFile` / `ContentResolver`

### 目前實作

Flutter 端透過 `MethodChannel` 呼叫 Android 原生層：

- `pickWorkspace`
- `listDirectory`
- `readTextFile`
- `writeTextFileIfUnchanged`

App 端記住的是：

- tree URI
- 顯示名稱
- tree 內的 archive 相對路徑

而不是一般 filesystem absolute path。

### 工作目錄解析順序

選到一個資料夾後，會依序判斷：

1. 若有 `data/settings.json` 且可讀到 `translation.data_dir`，優先使用它
2. 否則若所選資料夾本身就有 archive JSON，直接使用
3. 否則若有 `output/` 子目錄且內有 archive JSON，就切到 `output/`
4. 否則報錯

## 建置

### 需求

- Flutter 3.41.6 或相近版本
- Android SDK

### 安裝依賴

```bash
flutter pub get
```

### 分析

```bash
flutter analyze
```

### 測試

```bash
flutter test
```

### 產生 debug APK

```bash
flutter build apk --debug
```

本次實作已成功產生：

- `build/app/outputs/flutter-apk/app-debug.apk`

## 執行

```bash
flutter run
```

第一次啟動後：

1. 點右上角資料夾按鈕
2. 選擇 Syncthing 同步下來的資料夾
3. 若選的是 portable 根目錄，app 會嘗試讀取 `data/settings.json`
4. 進入列表並選擇條目開始編修

## 驗證結果

已完成的驗證：

- `flutter analyze` 通過
- `flutter test` 通過
- `flutter build apk --debug` 成功

## 目前限制

- 尚未提供自動草稿保存
- 尚未做超大 JSON 的分頁 / lazy loading
- 尚未加入上一筆 / 下一筆快捷跳轉
- 設定保存在 app-private storage，不會回寫桌面版 `data/settings.json`

## 參考

- [Android documents and files training](https://developer.android.com/training/data-storage/shared/documents-files)
- [AndroidX DocumentFile reference](https://developer.android.com/reference/androidx/documentfile/provider/DocumentFile)
