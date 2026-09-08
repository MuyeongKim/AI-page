"""Capture the current Windows GUI for the versioned user manual."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if os.name == "nt":
    os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["QT_SCALE_FACTOR"] = "1"

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mypackage.gui import Ui_MainWindow  # noqa: E402
from mypackage.version import CURRENT_RELEASE  # noqa: E402


def main():
    application = QApplication.instance() or QApplication([])
    window = Ui_MainWindow()
    # Render the actual widgets without opening a user-facing window or fetching notices.
    window._online_notice_fetch_started = True
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.resize(760, 760)
    window.show()
    application.processEvents()
    output = ROOT / "docs" / "images" / f"manual-main-{CURRENT_RELEASE.display_version}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not window.grab().save(str(output)):
            raise RuntimeError(f"Could not save GUI screenshot: {output}")
        print(f"Created {output}")
    finally:
        window._closing_without_confirmation = True
        window.close()
        window.deleteLater()
        application.processEvents()


if __name__ == "__main__":
    main()
