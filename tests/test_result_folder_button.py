from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton

from mypackage import gui


@pytest.fixture
def window(qt_application, monkeypatch):
    monkeypatch.setattr(gui, "get_preferred_device", lambda: "cpu")
    monkeypatch.setattr(gui.MemoryMonitor, "log_memory_usage", lambda *_args: None)
    main_window = gui.Ui_MainWindow()
    main_window._online_notice_fetch_started = True
    yield main_window
    main_window.worker = None
    main_window._closing_without_confirmation = True
    main_window.close()
    main_window.deleteLater()
    qt_application.processEvents()


def _remember_result(window, folder, status="completed"):
    window.remember_detection_result(
        {"source": "사진", "status": status, "output_folder": str(folder) if folder else None},
        "작업 종료",
    )


def test_result_folder_button_starts_disabled(window):
    assert window.open_output_button.text() == "저장 폴더 열기"
    assert not window.open_output_button.isEnabled()
    assert window.resultCard.isAncestorOf(window.open_output_button)


def test_detection_target_controls_share_one_row_at_minimum_width(window, qt_application):
    window.resize(560, 560)
    window.show()
    qt_application.processEvents()
    viewport = window.scrollArea.viewport()
    controls = [window.radioButton_all, window.radioButton_person, window.radioButton_car]
    centers = [control.mapTo(viewport, control.rect().center()) for control in controls]

    assert window.minimumWidth() <= 560
    assert window.radioButton_all.text() == "전체"
    assert [point.x() for point in centers] == sorted(point.x() for point in centers)
    assert max(point.y() for point in centers) - min(point.y() for point in centers) <= 1
    assert all(0 <= point.x() < viewport.width() for point in centers)
    assert window.findChild(QPushButton, "pushButton_open_output_folder") is None


@pytest.mark.parametrize("status", ["completed", "partial", "cancelled", "failed", "disconnected"])
def test_results_tab_can_open_preserved_run_folder(window, tmp_path, status, monkeypatch):
    folder = tmp_path / "20260908_143025"
    folder.mkdir()
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)

    _remember_result(window, folder, status)
    window.open_output_button.click()

    assert window.open_output_button.isEnabled()
    assert len(opened) == 1
    assert Path(opened[0].toLocalFile()) == folder.resolve()


def test_latest_result_replaces_previous_run_folder(window, tmp_path, monkeypatch):
    folders = [tmp_path / name for name in ("20260908_143025", "20260908_143025_1")]
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    for folder in folders:
        folder.mkdir()
        _remember_result(window, folder)

    window.open_output_button.click()

    assert len(opened) == 1
    assert Path(opened[0].toLocalFile()) == folders[-1].resolve()


def test_model_failure_does_not_link_to_previous_run_folder(window, tmp_path):
    _remember_result(window, tmp_path)
    assert window.open_output_button.isEnabled()

    _remember_result(window, None, "failed")

    assert not window.open_output_button.isEnabled()


def test_result_folder_button_warns_when_os_rejects_existing_folder(
    window, tmp_path, monkeypatch
):
    warnings = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda _url: False)
    monkeypatch.setattr(
        gui.QMessageBox, "warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )
    _remember_result(window, tmp_path)

    window.open_output_button.click()

    assert warnings == [("결과 열기", "파일을 열지 못했습니다. 저장 폴더를 확인해 주세요.")]
    assert window.open_output_button.isEnabled()


def test_result_folder_button_disables_when_completed_folder_was_removed(
    window, tmp_path, monkeypatch
):
    folder = tmp_path / "20260908_143025"
    folder.mkdir()
    warnings = []
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", opened.append)
    monkeypatch.setattr(
        gui.QMessageBox, "warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )
    _remember_result(window, folder)
    folder.rmdir()

    window.open_output_button.click()

    assert opened == []
    assert warnings == [("결과 열기", "파일이 이동되었거나 삭제되었습니다.")]
    assert not window.open_output_button.isEnabled()
