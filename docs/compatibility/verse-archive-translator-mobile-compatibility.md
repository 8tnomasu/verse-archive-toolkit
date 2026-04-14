# VerseArchiveTranslator 行動版相容性說明

本文件描述 Flutter Android 版相對於桌面版 VerseArchiveTranslator 的相容性現況。

## 完全相容

### JSON schema

目前保存與讀取維持桌面版使用的核心欄位結構：

- `type`
- `title.en`
- `title.cn`
- `author.en`
- `author.cn`
- `content.lines`
- `content.en`
- `content.cn`

### 保存語意

保存時：

- 只更新 `title.cn`
- 只更新 `author.cn`
- 只更新 `content.cn`
- 不會改寫 `content.lines`
- 不會移除既有 review metadata

### translation state

與桌面版一致：

- 只用 `title.en`、`author.en`、`content.en` 判定 translated / partial / untranslated
- `content.lines` 不參與翻譯完成判定

### 搜尋與 random

與桌面版一致：

- 搜尋會搜尋 `author.en`、`title.en`、`content.en`、`content.lines`
- visible list 只受 search query 與 type filter 影響
- translation filter 只影響 random pick

### 載入規則

與桌面版一致：

- 標準檔存在時優先只載入標準檔
- 否則回退到 `*.json`
- 空 JSON list 會跳過

### 衝突檢查

與桌面版一致：

- 保存前先檢查檔案修改時間
- 再檢查 record signature

## 部分相容

### `translation.data_dir` 解析

桌面版可以把相對路徑與絕對路徑交給一般檔案系統解析。

Android 版目前相容範圍：

- 相對子目錄，例如 `output`
- `.` 視為目前 tree 根目錄
- portable toolkit 根目錄下的 `output/`

Android 版目前不直接相容的情況：

- 指向 tree 外部的絕對路徑
- 需要跳出目前 tree 的 `..` 路徑

原因是 Android SAF 的權限模型只允許在已授權 tree 內操作。

### recent workspace 恢復

Android 版保存的是：

- `treeUri`
- `archiveRelativePath`
- `resolutionSource`

只要 persisted URI permission 仍有效，App 重開後即可恢復。

若使用者在系統層撤銷了文件存取權限，bookmark 仍會存在，但重新載入會失敗並顯示錯誤。

## 延後處理

- 真機層級的 SAF instrumentation tests
- 更細的外部修改 diff / merge UI
- 超大 archive 的增量載入
- 桌面版前後筆快速瀏覽的完整操作體驗

## 驗收後新增確認

本次嚴格驗收額外確認並修正：

- 清單不再誤用 translation filter
- 空 JSON list 不再被當成有效 document
- save 不再接受 mtime 已變更的檔案
- README 與架構文件已同步更新為實際語意
