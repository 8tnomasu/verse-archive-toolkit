# VerseArchiveTranslator Flutter Android App

This Flutter app keeps the desktop `VerseArchiveTranslator` workflow focused on manual translation and manual revision. It works directly on locally synced files, especially folders synced to Android through Syncthing.

## Scope

- Android-first Flutter UI
- Local folder access through Android Storage Access Framework
- Desktop-compatible archive JSON input and output
- Manual editing of `title.cn`, `author.cn`, and `content.cn`
- Desktop-compatible search, save, and random-pick semantics

## Current mobile UI structure

The phone UI is intentionally compact:

- The AppBar keeps the active workspace name and the main actions.
- Workspace picking is handled by the folder action.
- Recent workspaces open from the history action.
- Workspace details, archive root, resolution notes, and tree URI live in a bottom sheet instead of a large card on the main screen.
- The bottom tabs remain:
  - `List`
  - `Edit`

### List tab

The list tab keeps only the high-frequency tools:

- Search field
- Type filter
- Random scope filter
- Compact visible-results summary
- Result list

Visible-results summary is computed from the current visible list only:

- `search query` and `type filter` determine visible results
- translated / partial / untranslated counts are computed from those visible results
- `translation filter` does not affect visible results or visible summary
- `translation filter` only affects random pick

### Edit tab

The editor focuses on the translation workflow:

- Compact record header
- Source section
- Translation section
- Optional expandable metadata section
- Low-height sync / save bar

## Keyboard handling

Phone layout now avoids the previous overflow and keyboard issues by combining:

- `Scaffold.resizeToAvoidBottomInset`
- A scrollable editor body
- `Scrollable.ensureVisible` for focused translation fields
- Extra bottom padding inside the editor scroll view
- Hiding the bottom navigation bar while the keyboard is open

This prevents the previous `BOTTOM OVERFLOWED BY 76 PIXELS` failure mode caused by a fixed in-body bottom navigation area competing with the editor layout.

## Build and run

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
flutter run
```

Debug APK output:

- `build/app/outputs/flutter-apk/app-debug.apk`

## Notes

- This app does not change the desktop JSON schema.
- It does not change repository logic, save semantics, search semantics, random semantics, or translation-state semantics.
- Large-data lazy loading is still out of scope for this phase.
