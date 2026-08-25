import math
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from mypackage import gui


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def main_window(qapp):
    window = gui.Ui_MainWindow()
    yield window

    worker = window.worker
    if worker is not None and hasattr(worker, "isRunning") and worker.isRunning():
        worker.stop()
        if hasattr(worker, "wait"):
            worker.wait(5_000)
    window.worker = None
    window.close_progress_dialog()
    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    qapp.processEvents()


def _solid_image(red):
    image = QImage(4, 4, QImage.Format.Format_RGB32)
    image.fill(QColor(red, 0, 0))
    return image


def test_preview_mailbox_keeps_only_latest_frame_until_gui_tick(main_window, qapp):
    main_window.show_preview_window("연결 중")
    main_window._preview_timer.stop()
    qapp.processEvents()

    presented = []
    status_updates = []
    main_window.preview_window.set_preview_pixmap = presented.append
    main_window.preview_window.set_status = status_updates.append

    frames = [_solid_image(red) for red in range(50)]
    for frame in frames:
        main_window.update_preview_frame(frame)

    assert presented == []
    assert status_updates == []
    assert main_window._pending_preview_frame is frames[-1]
    assert main_window._preview_timer.interval() == gui.PREVIEW_REFRESH_INTERVAL_MS

    main_window._display_pending_preview_frame()
    main_window._display_pending_preview_frame()

    assert len(presented) == 1
    assert presented[0].toImage().pixelColor(0, 0).red() == 49
    assert status_updates == ["실시간 탐지 프레임을 표시하는 중입니다."]
    assert main_window._pending_preview_frame is None


class _BurstWorker(QThread):
    progress_signal = Signal(int, str)
    error_signal = Signal(str)
    finished_signal = Signal(dict)
    log_signal = Signal(str)
    frame_signal = Signal(object)

    instances = []

    def __init__(self, _params):
        super().__init__()
        self.keep_running = True
        self.emitted_count = 0
        self.instances.append(self)

    def run(self):
        for index in range(120):
            if not self.keep_running:
                break
            self.frame_signal.emit(_solid_image(index % 100))
            self.emitted_count += 1
            self.msleep(1)

    def stop(self):
        self.keep_running = False


def test_worker_frame_burst_is_rendered_only_by_bounded_gui_timer(
    main_window, qapp, tmp_path, monkeypatch
):
    source = tmp_path / "input.mp4"
    source.touch()
    render_threads = []

    def record_render(_preview_window, _pixmap):
        render_threads.append(QThread.currentThread())

    _BurstWorker.instances.clear()
    monkeypatch.setattr(gui, "DetectionWorker", _BurstWorker)
    monkeypatch.setattr(gui.PreviewWindow, "set_preview_pixmap", record_render)

    main_window.source = gui.VIDEO_FILE_SOURCE
    main_window.juso = [str(source)]
    main_window.datasize = "fake-model.pt"
    main_window.file_count = 1
    started_at = time.monotonic()
    main_window.submit()

    deadline = time.monotonic() + 3
    while main_window.worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.002)
    qapp.processEvents()

    worker = _BurstWorker.instances[0]
    elapsed_seconds = time.monotonic() - started_at
    maximum_timer_renders = (
        math.ceil(elapsed_seconds * 1_000 / gui.PREVIEW_REFRESH_INTERVAL_MS) + 1
    )
    assert worker.emitted_count == 120
    assert 1 <= len(render_threads) <= maximum_timer_renders
    assert len(render_threads) < worker.emitted_count
    assert all(thread is qapp.thread() for thread in render_threads)
    assert not main_window._preview_timer.isActive()
    assert main_window._pending_preview_frame is None
    assert main_window._preview_accepting_frames is False


class _SlowStoppingWorker:
    def __init__(self):
        self.stop_calls = 0

    def isRunning(self):
        return True

    def stop(self):
        self.stop_calls += 1


def test_cancel_is_idempotent_and_keeps_dialog_until_worker_exit(main_window, qapp):
    worker = _SlowStoppingWorker()
    main_window.worker = worker
    main_window.progress_dialog = gui.DetectionProgressDialog("처리 중", 0, main_window)
    main_window.progress_dialog.show()
    main_window.show_preview_window("탐지 중")
    main_window.update_preview_frame(_solid_image(10))
    qapp.processEvents()

    main_window.cancel_detection()
    main_window.cancel_detection()
    qapp.processEvents()

    assert worker.stop_calls == 1
    assert main_window.progress_dialog.isVisible()
    assert "취소 요청됨" in main_window.progress_dialog.label.text()
    assert not main_window.progress_dialog.cancel_button.isEnabled()
    assert not main_window._preview_timer.isActive()
    assert main_window._pending_preview_frame is None
    assert main_window._preview_accepting_frames is False

    main_window.worker = None
    main_window.close_progress_dialog()
    qapp.processEvents()
    assert main_window.progress_dialog is None
