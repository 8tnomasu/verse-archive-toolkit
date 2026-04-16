from __future__ import annotations

from verse_archive_toolkit.gui.builder_app import BuilderMainWindow
from verse_archive_toolkit.runtime import run_gui_application


def main(argv: list[str] | None = None) -> int:
    return run_gui_application(
        app_slug="builder-gui",
        app_title="VerseArchiveCurator",
        window_factory=BuilderMainWindow,
        argv=argv,
        also_console=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
