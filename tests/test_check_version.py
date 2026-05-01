import importlib
import pathlib
import sys
import types


def test_get_latest_version_skips_http_request_when_offline(monkeypatch):
    check_version = load_check_version_with_qt_stubs()
    request_calls = []

    def fake_get(*args, **kwargs):
        request_calls.append((args, kwargs))
        raise check_version.requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(check_version, "has_internet_connection", lambda: False, raising=False)
    monkeypatch.setattr(check_version.requests, "get", fake_get)

    result = check_version.get_latest_version()

    assert result == "NO_CONNECTION"
    assert request_calls == []


def test_get_latest_version_requests_server_when_network_is_available(monkeypatch):
    check_version = load_check_version_with_qt_stubs()
    request_calls = []

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"version": "26.04.10"}

    def fake_get(*args, **kwargs):
        request_calls.append((args, kwargs))
        return DummyResponse()

    monkeypatch.setattr(check_version, "has_internet_connection", lambda: True, raising=False)
    monkeypatch.setattr(check_version.requests, "get", fake_get)

    result = check_version.get_latest_version()

    assert result == "26.04.10"
    assert len(request_calls) == 1


def load_check_version_with_qt_stubs():
    project_root = pathlib.Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    qtwidgets = types.ModuleType("PySide6.QtWidgets")

    class DummyQApplication:
        _instance = None

        def __init__(self, *args, **kwargs):
            DummyQApplication._instance = self

        @staticmethod
        def instance():
            return DummyQApplication._instance

        def quit(self):
            return None

    class DummyMessageBox:
        class Icon:
            Information = 1
            Warning = 2
            Critical = 3

        class StandardButton:
            Ok = 0

        def setWindowTitle(self, *args, **kwargs):
            return None

        def setText(self, *args, **kwargs):
            return None

        def setIcon(self, *args, **kwargs):
            return None

        def setStandardButtons(self, *args, **kwargs):
            return None

        def setStyleSheet(self, *args, **kwargs):
            return None

        def exec(self):
            return 0

    qtwidgets.QApplication = DummyQApplication
    qtwidgets.QMessageBox = DummyMessageBox

    pyside6 = types.ModuleType("PySide6")
    pyside6.QtWidgets = qtwidgets

    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules.pop("mypackage.check_version", None)
    return importlib.import_module("mypackage.check_version")
