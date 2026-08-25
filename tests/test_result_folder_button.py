import os
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mypackage import gui


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def window(qapp, monkeypatch):
    monkeypatch.setattr(gui, "get_preferred_device", lambda: "cpu")
    monkeypatch.setattr(gui.MemoryMonitor, "log_memory_usage", lambda *_args: None)
    main_window = gui.Ui_MainWindow()
    yield main_window

    main_window.worker = None
    main_window._closing_without_confirmation = True
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


def _terminal_result(output_folder):
    return {
        "source": "사진",
        "status": gui.DETECTION_STATUS_COMPLETED,
        "output_folder": str(output_folder),
    }


def test_result_folder_button_starts_disabled(window):
    assert window.pushButton_open_output_folder.text() == "탐지 폴더 열기"
    assert not window.pushButton_open_output_folder.isEnabled()


def test_result_folder_button_fits_at_minimum_window_width(window, qapp):
    window.resize(560, 560)
    window.show()
    qapp.processEvents()

    button = window.pushButton_open_output_folder
    button_left = button.mapTo(window.scrollArea.viewport(), button.rect().topLeft()).x()
    button_right = button.mapTo(window.scrollArea.viewport(), button.rect().topRight()).x()

    assert window.minimumWidth() <= 560
    assert button_left >= 0
    assert button_right <= window.scrollArea.viewport().width()


def test_result_folder_button_enables_only_after_processing_finishes(window, tmp_path):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()

    window.set_processing_state(True)
    window.on_detection_finished(_terminal_result(output_folder))

    assert not window.pushButton_open_output_folder.isEnabled()

    window.set_processing_state(False)

    assert window.pushButton_open_output_folder.isEnabled()


def test_starting_new_detection_clears_previous_output_folder(window, tmp_path):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()

    window.on_detection_finished(_terminal_result(output_folder))
    window.set_processing_state(False)
    assert window.pushButton_open_output_folder.isEnabled()

    window.set_processing_state(True)

    assert window._detection_output_folder is None
    assert not window.pushButton_open_output_folder.isEnabled()


@pytest.mark.parametrize(
    "status",
    [
        gui.DETECTION_STATUS_FAILED,
        gui.DETECTION_STATUS_CANCELLED,
        gui.DETECTION_STATUS_DISCONNECTED,
    ],
)
def test_unsuccessful_detection_does_not_enable_previous_output_folder(
    window, tmp_path, status
):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()
    result = _terminal_result(output_folder)
    result["status"] = status

    window.set_processing_state(True)
    window.on_detection_finished(result)
    window.set_processing_state(False)

    assert window._detection_output_folder is None
    assert not window.pushButton_open_output_folder.isEnabled()


def test_result_folder_button_opens_exact_worker_output_folder(window, tmp_path, monkeypatch):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()
    opened_urls = []

    def open_url(url):
        opened_urls.append(url)
        return True

    monkeypatch.setattr(gui.QDesktopServices, "openUrl", open_url)

    window.on_detection_finished(_terminal_result(output_folder))
    window.set_processing_state(False)
    window.pushButton_open_output_folder.click()

    assert len(opened_urls) == 1
    assert Path(opened_urls[0].toLocalFile()) == output_folder.resolve()


def test_result_folder_button_warns_when_os_rejects_existing_folder(
    window, tmp_path, monkeypatch
):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()
    warnings = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda _url: False)
    monkeypatch.setattr(
        gui.QMessageBox,
        "warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )

    window.on_detection_finished(_terminal_result(output_folder))
    window.set_processing_state(False)
    window.pushButton_open_output_folder.click()

    assert warnings == [
        ("탐지 폴더 열기", "운영체제에서 탐지 결과 폴더를 열지 못했습니다.")
    ]
    assert window.pushButton_open_output_folder.isEnabled()


def test_result_folder_button_disables_when_completed_folder_was_removed(
    window, tmp_path, monkeypatch
):
    output_folder = tmp_path / "detected"
    output_folder.mkdir()
    warnings = []
    opened_urls = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", opened_urls.append)
    monkeypatch.setattr(
        gui.QMessageBox,
        "warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )

    window.on_detection_finished(_terminal_result(output_folder))
    window.set_processing_state(False)
    shutil.rmtree(output_folder)
    window.pushButton_open_output_folder.click()

    assert opened_urls == []
    assert warnings == [
        ("탐지 폴더 열기", "탐지 결과 폴더가 존재하지 않습니다. 다시 탐지를 실행해 주세요.")
    ]
    assert not window.pushButton_open_output_folder.isEnabled()
