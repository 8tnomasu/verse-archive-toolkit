# VerseArchiveToolkit

VerseArchiveToolkit is the umbrella project for building and translating verse archive JSON files.

VerseArchiveToolkit 是整個工具集合與 repository 名稱，用於建立、整理、維護與人工翻譯 verse archive JSON。

## Products

- `VerseArchiveCurator`: the desktop archive-building and archive-maintenance tool.
- `VerseArchiveTranslator Desktop`: the desktop manual translation and revision tool.
- `VerseArchiveTranslator Mobile`: the Flutter Android manual translation and revision tool.

## Naming policy

- `VerseArchiveToolkit` only refers to the repository, umbrella project, and tool suite.
- `VerseArchiveCurator` is the formal product name of the desktop archive-building tool.
- `VerseArchiveTranslator` remains the shared product name for both the desktop translator and the Flutter Android translator.
- Technical identifiers such as `verse-archive-toolkit`, `verse_archive_toolkit`, and the existing CLI command names are retained for compatibility.

## Quick start from a Windows release ZIP

1. Download the latest Windows ZIP from GitHub Releases.
2. Extract the ZIP to a local folder.
3. Run `VerseArchiveCurator.exe` to build or maintain archive JSON files.
4. If you need quote collection, fill in your `ZenQuotes API key`.
5. Choose the output folder and build options, then start the build.
6. After the build finishes, open `VerseArchiveTranslator.exe` from Curator or launch it directly for manual translation and revision.

## What each app does

- `VerseArchiveCurator` fetches data from PoetryDB and ZenQuotes, applies review / reject filter rules, and writes archive JSON files.
- `VerseArchiveTranslator Desktop` lets you search, review, and manually edit `title.cn`, `author.cn`, and `content.cn`.
- `VerseArchiveTranslator Mobile` keeps the same manual translation workflow on Android through Flutter and local synced folders.

## Python development

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional packaging dependencies:

```bash
python -m pip install -e .[packaging]
```

## Entrypoints

- `verse-archive-gui`: launches `VerseArchiveCurator`.
- `verse-archive-translator`: launches `VerseArchiveTranslator Desktop`.
- `verse-archive`: CLI entry for build, stats, and path diagnostics.

## Portable layout

All runtime data is stored next to the portable app folder:

```text
app-root/
  data/
    settings.json
  logs/
    builder-gui-*.log
    translator-gui-*.log
  output/
    english_poems.json
    philosophy_quotes.json
```

- `data/` stores local settings only.
- `logs/` stores runtime logs for the desktop apps.
- `output/` stores the generated archive JSON files.

The Flutter Android app can work with either the archive `output/` folder directly or a portable VerseArchiveToolkit root that contains `output/`.

## CLI notes

The CLI and Python package still keep compatibility-oriented technical names:

- package name: `verse-archive-toolkit`
- import path: `verse_archive_toolkit`
- CLI command: `verse-archive`
- GUI command: `verse-archive-gui`

These names are kept to avoid breaking existing development and automation workflows.

## Validation

Desktop / Python:

```bash
python -m pytest
```

Flutter Android, run inside `apps/verse_archive_translator_flutter`:

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

## Packaging

Build the Windows desktop apps:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-release.ps1
```

Debug build:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build-windows-debug.ps1
```

Release packaging keeps these product names:

- `VerseArchiveCurator`
- `VerseArchiveTranslator`

## Flutter Android app

The Android translator lives in `apps/verse_archive_translator_flutter/` and is the mobile edition of `VerseArchiveTranslator`.

Related docs:

- App README: `apps/verse_archive_translator_flutter/README.md`
- Desktop translator analysis: `docs/analysis/verse_archive_translator_desktop_analysis.md`
- Architecture: `docs/architecture/flutter-android-verse-archive-translator.md`
- Compatibility: `docs/compatibility/verse-archive-translator-mobile-compatibility.md`
- Roadmap: `docs/roadmap/flutter-android-verse-archive-translator-roadmap.md`

## Notes

- Keep your `ZenQuotes API key` local and do not commit it.
- This naming pass does not change JSON schema, archive read/write semantics, translator save semantics, search semantics, or random-pick semantics.
