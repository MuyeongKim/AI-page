import os
import time
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from mypackage import gps2, gui


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
    if worker is not None and worker.isRunning():
        worker.stop()
        worker.wait(5_000)
    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    qapp.processEvents()


def _worker_params(**overrides):
    params = {
        "source": "사진",
        "juso": [],
        "datasize": "fake-model.pt",
        "imgsz": 640,
        "percentage": 0.1,
        "device": "cpu",
        "classes_to_detect": list(gui.PERSON_AND_VEHICLE_CLASSES),
        "file_count": 0,
        "only_person": False,
        "only_car": False,
    }
    params.update(overrides)
    return params


def test_default_state_and_unselected_submit_warns_without_starting_worker(
    main_window, monkeypatch
):
    warnings = []
    monkeypatch.setattr(
        gui.QMessageBox,
        "warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )

    assert main_window.source is None
    assert main_window.datasize is None
    assert main_window.percentage == pytest.approx(0.1)
    assert main_window.classes_to_detect == [0, 2, 5, 7]

    main_window.submit()
    assert warnings[-1] == ("입력 확인", "입력 소스를 선택해 주세요.")
    assert main_window.worker is None

    main_window.comboBox_source.setCurrentText("사진")
    main_window.submit()
    assert warnings[-1] == ("입력 확인", "탐지 모델을 선택해 주세요.")
    assert main_window.worker is None


def test_detection_worker_processes_a_string_photo_path(tmp_path, monkeypatch):
    image_path = tmp_path / "single.jpg"
    image_path.write_bytes(b"not decoded because inference is mocked")
    worker = gui.DetectionWorker(_worker_params(juso=str(image_path), file_count=1))
    processed = []
    progress = []

    monkeypatch.setattr(
        worker,
        "process_single_file",
        lambda source, _detected, _output: processed.append(source),
    )
    worker.progress_signal.connect(
        lambda value, message: progress.append((value, message))
    )

    worker.process_images(tmp_path / "output", [])

    assert processed == [str(image_path)]
    assert worker.processed_count == 1
    assert progress == [(1, "진행 중... 1 / 1")]


def test_source_placeholder_and_browse_controls_reset(main_window):
    default_placeholder = "탐지할 파일 또는 폴더 경로를 선택하세요"

    main_window.comboBox_source.setCurrentText("외부영상(캡처보드)")
    main_window.lineEdit_juso.setText("2")
    assert "캡처 장치 번호" in main_window.lineEdit_juso.placeholderText()
    assert not main_window.pushButton_search.isEnabled()
    assert not main_window.pushButton_search_2.isEnabled()

    main_window.comboBox_source.setCurrentIndex(0)

    assert main_window.source is None
    assert main_window.juso is None
    assert main_window.file_count == 0
    assert main_window.lineEdit_juso.text() == ""
    assert main_window.lineEdit_juso.placeholderText() == default_placeholder
    assert main_window.pushButton_search.isEnabled()
    assert main_window.pushButton_search_2.isEnabled()


class _Scalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class _Box:
    def __init__(self, class_id):
        self.cls = _Scalar(class_id)


class _VideoResult:
    names = {0: "person", 2: "car", 5: "bus", 7: "truck"}

    def __init__(self, frame, class_ids):
        self._frame = frame
        self.boxes = [_Box(class_id) for class_id in class_ids]
        self.speed = {"preprocess": 1.0, "inference": 8.0, "postprocess": 1.0}

    def plot(self):
        return self._frame.copy()


class _VideoModel:
    def __init__(self, detections_by_frame):
        self._detections = iter(detections_by_frame)

    def __call__(self, frame, **_kwargs):
        return [_VideoResult(frame, next(self._detections))]


class _Capture:
    def __init__(self, frames, cv2_module):
        self._frames = iter(frames)
        self._cv2 = cv2_module
        self.released = False

    def isOpened(self):
        return True

    def get(self, property_id):
        if property_id == self._cv2.CAP_PROP_FRAME_WIDTH:
            return 64
        if property_id == self._cv2.CAP_PROP_FRAME_HEIGHT:
            return 48
        if property_id == self._cv2.CAP_PROP_FPS:
            return 30.0
        return 0

    def read(self):
        try:
            return True, next(self._frames)
        except StopIteration:
            return False, None

    def release(self):
        self.released = True


def test_video_counts_are_maximum_simultaneous_counts_per_class(
    qapp, tmp_path, monkeypatch
):
    frames = [
        np.zeros((48, 64, 3), dtype=np.uint8),
        np.zeros((48, 64, 3), dtype=np.uint8),
    ]
    capture = _Capture(frames, gui.cv2)
    worker = gui.DetectionWorker(
        _worker_params(source=gui.CAPTURE_BOARD_SOURCE, juso=None)
    )
    worker.model = _VideoModel(
        [
            [0, 0, 2],  # 2 people and 1 vehicle in frame 1
            [0, 2, 5, 7],  # 1 person and 3 vehicles in frame 2
        ]
    )
    monkeypatch.setattr(worker, "open_video_capture", lambda _source: capture)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)

    result = worker.process_video(tmp_path)

    assert result["had_detection"] is True
    assert result["frame_count"] == 2
    assert worker.total_people_detected == 2
    assert worker.total_cars_detected == 3
    assert capture.released is True


def test_worker_emits_cancelled_terminal_status(tmp_path, monkeypatch):
    emitted = []
    output_dir = tmp_path / "detected"
    worker = gui.DetectionWorker(_worker_params())
    worker.finished_signal.connect(emitted.append)

    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gui, "YOLO", lambda _model_source: object())
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    worker.stop()

    worker.run()

    assert len(emitted) == 1
    assert emitted[0]["status"] == "cancelled"
    assert emitted[0]["processed_count"] == 0
    assert emitted[0]["original_files"] == []
    assert emitted[0]["output_files"] == []


class _StoppableWorker(QThread):
    def __init__(self, stop_calls):
        super().__init__()
        self._keep_running = True
        self._stop_calls = stop_calls

    def run(self):
        while self._keep_running:
            self.msleep(1)

    def stop(self):
        self._stop_calls.append(True)
        self._keep_running = False


def test_exit_button_confirms_once_and_defers_close_until_worker_finishes(
    main_window, qapp, monkeypatch
):
    confirmations = []
    stop_calls = []
    worker = _StoppableWorker(stop_calls)
    worker.finished.connect(main_window.on_worker_thread_finished)
    main_window.worker = worker
    main_window.show()
    worker.start()

    deadline = time.monotonic() + 2
    while not worker.isRunning() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    assert worker.isRunning()

    monkeypatch.setattr(
        main_window,
        "confirm_exit",
        lambda: confirmations.append(True) or True,
    )

    main_window.pushButton_close.click()

    assert len(confirmations) == 1
    assert stop_calls == [True]
    assert main_window._close_requested is True
    assert main_window._close_after_worker is True
    assert main_window.isVisible()

    deadline = time.monotonic() + 2
    while main_window.worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    qapp.processEvents()

    assert main_window.worker is None
    assert main_window._close_after_worker is False
    assert main_window._closing_without_confirmation is True
    assert main_window._cleanup_done is True
    assert not main_window.isVisible()
    assert len(confirmations) == 1


def test_gps_processes_only_explicit_image_paths(tmp_path, monkeypatch):
    selected = tmp_path / "original_selected.jpg"
    stale = tmp_path / "original_stale.jpg"
    selected.write_bytes(b"selected")
    stale.write_bytes(b"stale")
    inspected = []
    plotted = []

    def fake_extract(path):
        inspected.append(Path(path).name)
        return (37.0, 127.0)

    def fake_plot(locations, output_html="map.html", open_browser=True):
        plotted.append((locations, Path(output_html), open_browser))

    monkeypatch.setattr(gps2, "extract_gps_data", fake_extract)
    monkeypatch.setattr(gps2, "plot_location_on_map", fake_plot)

    result = gps2.process_images_in_folder(
        tmp_path,
        image_paths=[selected],
    )

    assert result == 1
    assert inspected == [selected.name]
    assert stale.name not in inspected
    assert plotted == [([(37.0, 127.0)], Path("map.html"), True)]


def test_local_map_server_returns_404_for_sibling_files(tmp_path):
    map_file = tmp_path / "map.html"
    sibling_file = tmp_path / "private.txt"
    map_file.write_text("<html>map</html>", encoding="utf-8")
    sibling_file.write_text("must not be served", encoding="utf-8")

    port = gps2._ensure_local_http_server(map_file)
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/{map_file.name}", timeout=2
        ) as response:
            assert response.status == 200
            assert response.read() == b"<html>map</html>"

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/{sibling_file.name}", timeout=2
            )
        assert exc_info.value.code == 404
    finally:
        gps2._shutdown_local_http_server()
