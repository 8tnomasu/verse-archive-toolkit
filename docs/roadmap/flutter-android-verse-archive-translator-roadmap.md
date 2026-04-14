# Flutter Android 版 TODO / Roadmap

## 已完成的第一階段

- 建立新的 Flutter Android app 專案
- 完成與桌面版對應的資料模型
- 完成 archive root 解析邏輯
- 支援直接選取 output 目錄
- 支援選取 portable 根目錄並讀取 `data/settings.json`
- 支援 Android Storage Access Framework
- 支援 persisted URI permission
- 支援 recent workspaces
- 支援搜尋 / 類型篩選 / 翻譯狀態篩選
- 支援顯示原文與編輯譯文
- 支援保存單筆翻譯
- 支援未儲存變更提示
- 支援保存前衝突檢查
- 通過 `flutter analyze`
- 通過 `flutter test`
- 成功產出 debug APK

## 下一步優先事項

### P1

- 在編修頁加入「上一筆 / 下一筆」快速跳轉
- 加入更明確的保存成功 / 保存失敗提示條
- 顯示目前選中項目在列表中的位置
- 更細緻地顯示 review metadata

### P2

- 支援只顯示 review 檔內容
- 支援僅顯示未翻譯 / 部分完成的快捷篩選 chip
- 支援記住上次搜尋與篩選條件
- 提供更完整的載入警告明細頁

### P3

- 自動保存本地草稿
- 保存前產生 app-private rollback snapshot
- 更完整的外部變更重新比對機制
- 平板最佳化版面

## 可考慮但暫不優先

- 匯出編修進度摘要
- 批次檢查缺漏翻譯欄位
- 可選的唯讀模式
- 多工作區標籤切換

## 明確不在目前範圍

- AI 翻譯 / API 翻譯
- 雲端帳號系統
- 背景排程
- 背景同步
- 非 VerseArchiveTranslator 模組
- 大量與需求無關的狀態管理或架構抽象

## 風險與注意事項

- Android 上 SAF 的 `lastModified()` 精度可能低於桌面檔案系統
- 某些文件提供者的效能可能比直接 path IO 慢
- 超大型 JSON 檔在手機上仍可能需要後續做 lazy loading / paging
- 不同廠牌 Android 裝置對文件選取器的 UI 會有差異
