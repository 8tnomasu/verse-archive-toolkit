# Verse Archive Toolkit

`Verse Archive Toolkit` 是一個可安裝的 Python CLI，專門用來從公開 API 建立並整理兩類文本資料：

- 英文詩作 archive，來源為 PoetryDB
- 哲思語錄 archive，來源為 ZenQuotes

專案目前提供資料抓取、去重、品質篩選、review 輸出、CLI 執行方式與公開倉庫所需的基本交付文件。抓取結果與本機設定預設不納入 Git，適合作為公開 GitHub repo 的乾淨起點。

## Features

- `verse-archive build`：抓取並建立詩作與語錄資料集
- `verse-archive stats`：查看目前輸出檔案的筆數統計
- PoetryDB 與 ZenQuotes 來源分開管理，可單獨執行
- 自動將未通過篩選的內容寫入 review JSON，方便人工複核
- 支援 `.env` 或環境變數載入 `ZENQUOTES_API_KEY`
- 預設把 `output/`、`data/`、`.env`、build 產物與快取排除在版本控制外

## Project Layout

```text
.
├─ src/verse_archive_toolkit/
├─ tests/
├─ .env.example
├─ pyproject.toml
├─ README.md
└─ verse_archive_builder.py
```

`verse_archive_builder.py` 保留為相容入口，方便用舊習慣直接執行；正式入口則是安裝後的 `verse-archive` CLI。

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

若要建立 ZenQuotes 語錄資料，請先設定 API key：

```bash
copy .env.example .env
```

然後把 `.env` 中的 `ZENQUOTES_API_KEY` 換成你自己的值，或直接在 shell 設定環境變數。

## Usage

只建立詩作資料：

```bash
python verse_archive_builder.py build --source poems --poem-target 200
```

建立詩作與語錄資料：

```bash
verse-archive build --source all --poem-target 500 --quote-target 500
```

自訂輸出目錄：

```bash
verse-archive build --source quotes --output-dir output/demo
```

查看目前輸出統計：

```bash
verse-archive stats --output-dir output
```

## Generated Files

完成建置後會在輸出目錄產生：

- `english_poems.json`
- `english_poems_review.json`
- `philosophy_quotes.json`
- `philosophy_quotes_review.json`

前兩個是已通過篩選的主資料集，後兩個是待人工複核的 review 清單。

## Packaging

如果要建立發佈檔，可在安裝 `build` 後執行：

```bash
python -m build
```

產物會落在 `dist/`，而 `dist/` 已加入 `.gitignore`，不會污染版本控制。

## Quality Checks

專案目前提供標準函式庫測試，可直接執行：

```bash
python -m unittest discover -s tests
```

## Notes

- `data/` 目錄中的既有大型 JSON 目前視為本機資料快照，不再追蹤。
- ZenQuotes 金鑰已從程式碼中移除，請自行提供環境變數。
- 若要把既有遠端歷史也整理成公開安全版本，請額外檢查並處理舊 commit 中可能殘留的資料與憑證。
