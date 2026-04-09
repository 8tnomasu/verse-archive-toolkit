from __future__ import annotations

import ctypes
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable

from platformdirs import user_log_dir

from verse_archive_toolkit.settings import APP_AUTHOR, APP_NAME


def get_user_log_directory() -> Path:
    path = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_log_path(app_slug: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_user_log_directory() / f"{app_slug}-{timestamp}.log"


def _extract_runtime_options(argv: list[str]) -> tuple[list[str], int, bool, bool]:
    forwarded: list[str] = []
    autoclose_ms = 0
    console_log = False
    debug_qt_plugins = False

    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--autoclose-ms" and index + 1 < len(argv):
            try:
                autoclose_ms = max(0, int(argv[index + 1]))
            except ValueError:
                autoclose_ms = 0
            index += 2
            continue

        if value.startswith("--autoclose-ms="):
            try:
                autoclose_ms = max(0, int(value.split("=", 1)[1]))
            except ValueError:
                autoclose_ms = 0
            index += 1
            continue

        if value == "--console-log":
            console_log = True
            index += 1
            continue

        if value == "--debug-qt-plugins":
            debug_qt_plugins = True
            index += 1
            continue

        forwarded.append(value)
        index += 1

    return forwarded, autoclose_ms, console_log, debug_qt_plugins


def configure_runtime_logging(app_slug: str, *, also_console: bool = False) -> Path:
    log_path = create_log_path(app_slug)
    handlers: list[logging.Handler] = [logging.FileHandler(log_path, encoding="utf-8")]
    if also_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.info("啟動應用程式：%s", app_slug)
    logging.info("Python 執行檔：%s", sys.executable)
    logging.info("目前工作目錄：%s", Path.cwd())
    logging.info("Frozen：%s", getattr(sys, "frozen", False))
    if getattr(sys, "frozen", False):
        logging.info("PyInstaller _MEIPASS：%s", getattr(sys, "_MEIPASS", ""))
    return log_path


def show_fatal_message(title: str, message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        QMessageBox.critical(None, title, message)
    except Exception:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)


def install_exception_hooks(app_title: str, log_path: Path) -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:  # type: ignore[no-untyped-def]
        if issubclass(exc_type, KeyboardInterrupt):
            return
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.exception("未處理例外：\n%s", text)
        show_fatal_message(
            app_title,
            f"程式啟動或執行時發生錯誤。\n\n詳細資訊已寫入：\n{log_path}\n\n{text}",
        )

    sys.excepthook = handle_exception

    def threading_handler(args) -> None:  # type: ignore[no-untyped-def]
        handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    import threading

    threading.excepthook = threading_handler


def maybe_autoclose(window, autoclose_ms: int) -> None:
    if autoclose_ms <= 0:
        env_value = os.getenv("VERSE_ARCHIVE_TOOLKIT_AUTOCLOSE_MS", "").strip()
        if env_value:
            try:
                autoclose_ms = max(0, int(env_value))
            except ValueError:
                autoclose_ms = 0

    if autoclose_ms <= 0:
        return

    from PySide6.QtCore import QTimer

    logging.info("自動關閉計時器已設定：%s ms", autoclose_ms)
    QTimer.singleShot(autoclose_ms, window.close)


def run_gui_application(
    *,
    app_slug: str,
    app_title: str,
    window_factory: Callable[[], object],
    argv: list[str] | None = None,
    also_console: bool = False,
) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    forwarded_arguments, autoclose_ms, console_log, debug_qt_plugins = _extract_runtime_options(
        arguments
    )
    if debug_qt_plugins or os.getenv("VERSE_ARCHIVE_TOOLKIT_QT_DEBUG_PLUGINS", "").strip() == "1":
        os.environ.setdefault("QT_DEBUG_PLUGINS", "1")

    log_path = configure_runtime_logging(
        app_slug,
        also_console=(
            also_console
            or console_log
            or os.getenv("VERSE_ARCHIVE_TOOLKIT_LOG_TO_CONSOLE", "").strip() == "1"
        ),
    )
    install_exception_hooks(app_title, log_path)

    try:
        from PySide6.QtWidgets import QApplication

        logging.info("啟動參數：%s", arguments)
        app = QApplication.instance() or QApplication([sys.argv[0], *forwarded_arguments])
        window = window_factory()
        if hasattr(window, "show"):
            window.show()
        maybe_autoclose(window, autoclose_ms)
        logging.info("主視窗已建立：%s", type(window).__name__)
        exit_code = app.exec()
        logging.info("應用程式結束，exit code=%s", exit_code)
        return exit_code
    except Exception:
        logging.exception("GUI 啟動失敗")
        show_fatal_message(
            app_title,
            f"程式無法啟動，詳細資訊已寫入：\n{log_path}",
        )
        return 1
