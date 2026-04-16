# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path.cwd()
src_root = project_root / "src"
entry_script = src_root / "verse_archive_toolkit" / "builder_gui_entry.py"

pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")
hiddenimports = pyside_hiddenimports + collect_submodules("shiboken6")


a = Analysis(
    [str(entry_script)],
    pathex=[str(src_root)],
    binaries=pyside_binaries,
    datas=pyside_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VerseArchiveCurator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="VerseArchiveCurator",
)
