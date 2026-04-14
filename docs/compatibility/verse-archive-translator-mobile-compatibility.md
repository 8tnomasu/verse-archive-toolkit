# 與桌面版相容性說明

本文件說明 Flutter Android 版與桌面版 `VerseArchiveTranslator` 的相容程度。

## 完全相容

### JSON schema

以下欄位結構保持相容：

- `type`
- `title.en`
- `title.cn`
- `author.en`
- `author.cn`
- `content.lines`
- `content.en`
- `content.cn`

### 標準檔名

優先讀取以下檔名的邏輯保持一致：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

### 翻譯狀態判定

Flutter 版完全沿用桌面版的三態：

- `translated`
- `partial`
- `untranslated`

### 搜尋欄位

Flutter 版與桌面版一樣搜尋：

- `author.en`
- `title.en`
- `content.en`
- `content.lines`

### 保存語意

Flutter 版保存時：

- 只更新 `title.cn`
- 只更新 `author.cn`
- 只更新 `content.cn`
- 保留其他欄位
- 保留 `content.lines`

這點和桌面版一致。

## 部分相容

### 設定格式

桌面版：

- 使用 `data/settings.json`
- `translation.data_dir` 可為相對或絕對路徑

Flutter Android 版：

- 主要設定保存在 app-private `SharedPreferences`
- 但若使用者選到 portable 根目錄，會讀取桌面版 `data/settings.json` 的 `translation.data_dir`

因此：

- `translation.data_dir` 概念相容
- 設定實際儲存位置不完全相同

### 工作目錄表示

桌面版使用 filesystem path。  
Android 版使用：

- persisted tree URI
- tree 內相對路徑

這是平台差異造成的必要調整。

### 檔案衝突檢查

桌面版使用：

- `mtime_ns`
- record signature

Android 版使用：

- `DocumentFile.lastModified()`
- record signature

概念相同，但 Android 提供的時間戳精度通常比桌面版低。

## 刻意調整的行為

### 選目錄方式

桌面版：

- `QFileDialog.getExistingDirectory()`

Android 版：

- `ACTION_OPEN_DOCUMENT_TREE`
- persisted URI permission

這是為了讓 Syncthing 同步下來的資料夾能被長期重新打開。

### UI 佈局

桌面版：

- 固定雙欄 master/detail

Android 版：

- 手機：列表 / 編修切換
- 大螢幕：雙欄

底層資料流程沒有改，但互動形式為手機做了必要調整。

### 最近使用工作目錄

桌面版沒有特別強調最近工作目錄列表。  
Android 版加入 recent workspaces，原因是：

- tree URI 重新選取成本高
- 手機使用情境更需要快速重開 Syncthing 目錄

## 延後處理

以下項目目前尚未和桌面版完全對齊：

- 自動監看外部檔案變動
- 更細緻的批次編修流程
- 與桌面版共用同一份完整 settings storage
- 更進一步的 review-only workflow 輔助

## 總結

如果把相容性拆成兩層：

### 資料相容

目前屬於高相容：

- 同樣讀寫 JSON
- 同樣的欄位結構
- 同樣的保存欄位
- 同樣的搜尋與翻譯狀態語意

### 平台設定 / 互動相容

目前屬於部分相容：

- Android 必須改用 SAF 與 URI permission
- UI 必須改為手機友善模式
- 設定儲存位置不與桌面版完全相同

因此可判定這個初版是：

- **資料與輸出結果高相容**
- **設定與互動方式平台化調整**
