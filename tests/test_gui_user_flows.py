import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from mypackage import gui


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp, monkeypatch):
    messages = []
    for method in ("information", "warning", "critical"):
        monkeypatch.setattr(
            gui.QMessageBox, method,
            lambda _parent, title, message: messages.append((title, message)),
        )
    instance = gui.Ui_MainWindow()
    instance._online_notice_fetch_started = True
    instance._test_messages = messages
    instance.show()
    qapp.processEvents()
    yield instance
    if instance._gps_worker is not None:
        instance._gps_worker.requestInterruption()
        instance._gps_worker.wait(3000)
        qapp.processEvents()
    instance._closing_without_confirmation = True
    instance.close()
    instance.deleteLater()
    qapp.processEvents()


def test_escape_requests_cancel_once_and_preserves_progress_window(window, qapp):
    dialog = gui.DetectionProgressDialog("탐지 중", 100, window)
    requests = []
    dialog.canceled.connect(lambda: requests.append(True))
    dialog.show()
    qapp.processEvents()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    qapp.processEvents()
    assert requests == [True]
    assert dialog.isVisible()
    assert not dialog.cancel_button.isEnabled()
    assert "취소 요청됨" in dialog.label.text()
    dialog.set_stage_progress("다음 프레임", 2, 10)
    assert "취소 요청됨" in dialog.label.text()
    dialog.finish()
    assert not dialog.isVisible()


def test_scrolling_does_not_change_threshold_but_keyboard_still_can(window, qapp):
    combo = window.comboBox_percentage
    window.pushButton_close.setFocus()
    qapp.processEvents()
    event = QWheelEvent(
        QPointF(combo.rect().center()), QPointF(combo.mapToGlobal(combo.rect().center())),
        QPoint(), QPoint(0, -120), Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False,
    )
    qapp.sendEvent(combo, event)
    assert window.percentage == pytest.approx(0.1)
    combo.setFocus()
    QTest.keyClick(combo, Qt.Key.Key_Down)
    assert window.percentage == pytest.approx(0.15)


def test_unavailable_gpu_updates_visible_selection_and_runtime_together(window, monkeypatch):
    monkeypatch.setattr(gui.torch.cuda, "is_available", lambda: False)
    window.comboBox_device.setCurrentText("GPU")
    assert window.device == "cpu"
    assert window.comboBox_device.currentText() == "CPU"
    assert window._test_messages[-1][0] == "GPU 사용 불가"


def test_small_window_keeps_full_status_and_action_visible_while_scrolling(window, qapp):
    window.resize(560, 560)
    qapp.processEvents()
    scrollbar = window.scrollArea.verticalScrollBar()
    for value in (0, scrollbar.maximum()):
        scrollbar.setValue(value)
        qapp.processEvents()
        for widget in (window.status_label, window.pushButton_enter, window.pushButton_close):
            assert widget.visibleRegion().boundingRect() == widget.rect()
        assert window.scrollAreaWidgetContents.width() <= window.scrollArea.viewport().width()


def test_results_remain_accessible_with_complete_errors_and_photo_comparison(
    window, qapp, tmp_path, monkeypatch
):
    original = tmp_path / "original_sample.jpg"
    output = tmp_path / "detected_sample.jpg"
    for path in (original, output):
        Image.new("RGB", (32, 24), "green").save(path)
    errors = [f"bad-{index}.jpg: 읽기 실패" for index in range(6)]
    result = {
        "source": "사진", "status": "partial", "image_count": 7,
        "detected_files": ["sample.jpg"], "original_files": [str(original)],
        "output_files": [str(output)], "output_folder": str(tmp_path),
        "folder_status": "저장됨", "execution_time": 1.0,
        "total_people": 1, "total_cars": 0, "errors": errors,
        "attempted_count": 7, "succeeded_count": 1, "failed_count": 6,
    }
    window.display_results_new(result)
    assert all(error in window.result_summary.toPlainText() for error in errors)
    assert window.infoTabs.currentIndex() == window.result_tab_index
    assert window.open_output_button.isEnabled()
    assert window.compare_result_button.isEnabled()
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    window.open_output_button.click()
    assert opened[0].toLocalFile() == str(tmp_path)
    window.compare_result_button.click()
    qapp.processEvents()
    assert window._comparison_dialog.isVisible()
    window._comparison_dialog.close()
    output.unlink()
    window.open_result_button.click()
    assert "삭제" in window._test_messages[-1][1]


def _wait_for_gps(window, qapp):
    deadline = time.monotonic() + 5
    while window._gps_worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        QTest.qWait(10)
    qapp.processEvents()
    assert window._gps_worker is None


def test_gps_without_metadata_explains_outcome_and_restores_inputs(window, qapp, tmp_path):
    photo = tmp_path / "original_no_gps.jpg"
    Image.new("RGB", (16, 16)).save(photo)
    window.start_gps_mapping([str(photo)], str(tmp_path))
    assert window._processing
    _wait_for_gps(window, qapp)
    assert not window._processing
    assert window.progress_dialog is None
    assert "GPS 없음: 1장" in window.result_summary.toPlainText()
    assert "GPS 정보가 없습니다" in window._test_messages[-1][1]


def test_close_during_gps_waits_for_worker_without_destroying_running_thread(
    window, qapp, tmp_path, monkeypatch
):
    def slow_gps(*_args, should_cancel, **_kwargs):
        deadline = time.monotonic() + 3
        while not should_cancel() and time.monotonic() < deadline:
            time.sleep(0.005)
        raise InterruptedError()

    monkeypatch.setattr(gui.gps2, "process_image_paths_detailed", slow_gps)
    window.start_gps_mapping(["sample.jpg"], str(tmp_path))
    window._closing_without_confirmation = True
    window.close()
    assert window._close_after_gps
    assert window.isVisible()
    _wait_for_gps(window, qapp)
    assert not window.isVisible()


def test_notice_links_only_open_valid_https_urls(window, monkeypatch):
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    window.plainTextEdit_online_notice.anchorClicked.emit(QUrl("https://example.com/news"))
    window.plainTextEdit_online_notice.anchorClicked.emit(QUrl("file:///etc/passwd"))
    window.plainTextEdit_online_notice.anchorClicked.emit(QUrl("https://user:password@example.com"))
    assert [url.toString() for url in opened] == ["https://example.com/news"]
