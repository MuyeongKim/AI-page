"""Keep a single Qt application alive for the entire test process."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    # Qt's offscreen plugin needs an explicit font directory on Windows.
    font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    if font_directory.is_dir():
        os.environ.setdefault("QT_QPA_FONTDIR", str(font_directory))

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qt_application():
    # Qt's process-wide native resources must not be torn down and recreated
    # between authentication tests and the desktop widget tests.
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application
    application.processEvents()
