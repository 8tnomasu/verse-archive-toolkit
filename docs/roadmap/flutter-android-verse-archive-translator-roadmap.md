# Flutter Android VerseArchiveTranslator Roadmap

## 已完成的第一階段

- 建立可編譯 Flutter Android App
- 完成 Android SAF 目錄選取與 persisted permission
- 完成桌面版相容的 archive root 解析
- 完成 JSON 載入、搜尋、編輯、保存流程
- 完成 recent workspace bookmark 保存與恢復
- 完成基本單元測試與建置驗證
- 完成第一輪嚴格驗收與相容性修正

## 下一階段建議

### 1. Android 真機驗證

- 在實際 Syncthing tree 上驗證 persisted permission 長期可用性
- 驗證系統回收或權限撤銷後的錯誤回復流程
- 驗證不同 ROM / Android 版本下的 `DocumentFile.lastModified()` 表現

### 2. 可用性補強

- 增加前後筆快速移動
- 增加 entry 重新定位與捲動提示
- 在 metadata 區顯示更多 review 欄位
- 增加更明確的衝突提示 UI

### 3. 大型資料集支援

- 分頁或增量載入
- 更精細的檔案級快取
- 更快的搜尋索引策略

### 4. 測試補強

- Android instrumentation tests
- 實際 SAF 權限中斷情境測試
- 更完整的 controller / widget tests

## 明確不在目前範圍

- AI / API 翻譯
- 帳號系統
- 雲端同步平台
- 背景翻譯排程
- 與 VerseArchiveTranslator 無關的其他 toolkit 模組
