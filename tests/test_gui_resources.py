import re

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QMainWindow

from mypackage import modern_gui_fixed


def test_dropdown_icon_renders_without_external_bundled_files(
    qt_application, tmp_path, monkeypatch
):
    module_path = tmp_path / "한글 배포본" / "_internal" / "mypackage" / "modern_gui_fixed.py"
    monkeypatch.setattr(modern_gui_fixed, "__file__", str(module_path))
    messages = []
    previous = qInstallMessageHandler(lambda _kind, _context, message: messages.append(message))
    window = QMainWindow()
    try:
        ui = modern_gui_fixed.ModernUi_MainWindow()
        ui.setupUi(window)
        window.show()
        qt_application.processEvents()
        assert not window.grab().isNull()
        arrow_url = re.search(r'QComboBox::down-arrow\s*\{\s*image: url\("([^"]+)"\)',
                              window.styleSheet()).group(1)
        assert QSvgRenderer(arrow_url).isValid(), messages
        assert not any("Cannot open file" in message for message in messages)
    finally:
        window.close()
        window.deleteLater()
        qt_application.processEvents()
        qInstallMessageHandler(previous)
