import importlib
import pathlib
import sys
import types
from typing import ClassVar


def test_prompt_for_key_uses_dialog_instance_in_password_mode(monkeypatch):
    start, input_dialog = load_start_with_qt_stubs(monkeypatch)

    user_key, accepted = start._prompt_for_key("Authentication", "Enter key")

    dialog = input_dialog.instances[-1]
    assert user_key == "stayup"
    assert accepted is True
    assert dialog.window_title == "Authentication"
    assert dialog.label_text == "Enter key"
    assert dialog.echo_mode == 1
    assert dialog.exec_calls == 1


def load_start_with_qt_stubs(monkeypatch):
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    qtwidgets = types.ModuleType("PySide6.QtWidgets")

    class DummyQApplication:
        @staticmethod
        def instance():
            return None

    class DummyQDialog:
        class DialogCode:
            Accepted = 1

    class DummyQInputDialog:
        instances: ClassVar[list] = []

        def __init__(self):
            self.window_title = None
            self.label_text = None
            self.echo_mode = None
            self.exec_calls = 0
            self.instances.append(self)

        @staticmethod
        def getText(*args, **kwargs):
            raise AssertionError("The static QInputDialog.getText() overload must not be used")

        def setWindowTitle(self, title):
            self.window_title = title

        def setLabelText(self, label):
            self.label_text = label

        def setTextEchoMode(self, echo_mode):
            self.echo_mode = echo_mode

        def exec(self):
            self.exec_calls += 1
            return DummyQDialog.DialogCode.Accepted

        def textValue(self):
            return "stayup"

    class DummyQLineEdit:
        class EchoMode:
            Password = 1

    class DummyMessageBox:
        pass

    qtwidgets.QApplication = DummyQApplication
    qtwidgets.QDialog = DummyQDialog
    qtwidgets.QInputDialog = DummyQInputDialog
    qtwidgets.QLineEdit = DummyQLineEdit
    qtwidgets.QMessageBox = DummyMessageBox

    pyside6 = types.ModuleType("PySide6")
    pyside6.QtWidgets = qtwidgets

    monkeypatch.setitem(sys.modules, "PySide6", pyside6)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)
    monkeypatch.delitem(sys.modules, "mypackage.start", raising=False)
    return importlib.import_module("mypackage.start"), DummyQInputDialog
