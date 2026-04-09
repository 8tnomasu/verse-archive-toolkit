$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m PyInstaller `
  --clean `
  --noconsole `
  --name VerseArchiveToolkit `
  --paths src `
  --collect-all PySide6 `
  src/verse_archive_toolkit/gui/builder_app.py

python -m PyInstaller `
  --clean `
  --noconsole `
  --name VerseArchiveTranslator `
  --paths src `
  --collect-all PySide6 `
  src/verse_archive_toolkit/gui/translator_app.py
