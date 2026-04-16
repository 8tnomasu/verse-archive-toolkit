from __future__ import annotations

from verse_archive_toolkit.gui.translator_app import TranslationWindow
from verse_archive_toolkit.runtime import run_gui_application


def main(argv: list[str] | None = None) -> int:
    return run_gui_application(
        app_slug="translator-gui",
        app_title="VerseArchiveTranslator",
        window_factory=TranslationWindow,
        argv=argv,
        also_console=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
