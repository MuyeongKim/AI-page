"""Keep a single Qt application alive for the entire test process."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
