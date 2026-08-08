import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from mypackage import gui


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


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


class _PhotoBoxes:
    cls = np.array([0])


class _PhotoResult:
    names = {0: "person"}
    boxes = _PhotoBoxes()

    def __init__(self, stale_dir):
        self.save_dir = str(stale_dir)

    def save(self, filename):
        Path(filename).write_bytes(b"CURRENT_RESULT")


def test_photo_saves_current_result_without_reusing_stale_same_stem(tmp_path):
    source = tmp_path / "same.png"
    source.write_bytes(b"CURRENT_SOURCE")
    stale_dir = tmp_path / "runs" / "detect" / "predict"
    stale_dir.mkdir(parents=True)
    (stale_dir / "same.jpg").write_bytes(b"STALE_RESULT")
    output_dir = tmp_path / "detected"
    model_calls = []

    worker = gui.DetectionWorker(
        _worker_params(juso=[str(source)], file_count=1, only_person=True)
    )

    def model(_source, **kwargs):
        model_calls.append(kwargs)
        return [_PhotoResult(stale_dir)]

    worker.model = model
    detected_files = []
    worker.process_single_file(str(source), detected_files, output_dir)

    assert worker.errors == []
    assert detected_files == [str(source)]
    assert model_calls[0]["save"] is False
    assert "project" not in model_calls[0]
    assert Path(worker.output_files[0]).read_bytes() == b"CURRENT_RESULT"
    assert Path(worker.original_files[0]).read_bytes() == b"CURRENT_SOURCE"
    assert not any("partial" in path.name for path in output_dir.iterdir())


class _Capture:
    def __init__(self, cv2_module, frames=1):
        self.cv2 = cv2_module
        self.frames = frames
        self.released = False

    def isOpened(self):
        return True

    def get(self, property_id):
        if property_id == self.cv2.CAP_PROP_FRAME_WIDTH:
            return 8
        if property_id == self.cv2.CAP_PROP_FRAME_HEIGHT:
            return 8
        if property_id == self.cv2.CAP_PROP_FPS:
            return 30.0
        return 0

    def read(self):
        if self.frames:
            self.frames -= 1
            return True, np.zeros((8, 8, 3), dtype=np.uint8)
        return False, None

    def release(self):
        self.released = True


class _VideoResult:
    boxes = []
    names = {}
    speed = {"inference": 1.0}

    def plot(self):
        return np.zeros((8, 8, 3), dtype=np.uint8)


def _video_worker(source):
    worker = gui.DetectionWorker(
        _worker_params(source=gui.VIDEO_FILE_SOURCE, juso=[str(source)], file_count=1)
    )
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    return worker


def _patch_video_runtime(monkeypatch, worker, writer_factory, frames=1):
    capture = _Capture(gui.cv2, frames=frames)
    monkeypatch.setattr(worker, "open_video_capture", lambda _source: capture)
    monkeypatch.setattr(gui.cv2, "VideoWriter", writer_factory)
    monkeypatch.setattr(gui.cv2, "VideoWriter_fourcc", lambda *_args: 0)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    return capture


def test_zero_byte_video_is_rejected_and_partial_is_removed(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = _video_worker(source)

    class ZeroByteWriter:
        def __init__(self, filename, *_args):
            self.path = Path(filename)
            self.path.touch()

        def isOpened(self):
            return True

        def write(self, _frame):
            pass

        def release(self):
            pass

    capture = _patch_video_runtime(monkeypatch, worker, ZeroByteWriter)

    with pytest.raises(RuntimeError, match="정상적으로 저장되지 않았습니다"):
        worker.process_video(output_dir)

    assert capture.released is True
    assert worker.output_files == []
    assert list(output_dir.iterdir()) == []


def test_cancelled_video_removes_partial_and_reports_no_output(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = _video_worker(source)

    class CancellingWriter:
        def __init__(self, filename, *_args):
            self.path = Path(filename)
            self.path.write_bytes(b"PARTIAL")
            worker.stop()

        def isOpened(self):
            return True

        def write(self, _frame):
            raise AssertionError("cancellation before the first read must skip writes")

        def release(self):
            pass

    _patch_video_runtime(monkeypatch, worker, CancellingWriter)

    result = worker.process_video(output_dir)

    assert worker.is_running is False
    assert result["frame_count"] == 0
    assert result["output_file"] is None
    assert worker.output_files == []
    assert list(output_dir.iterdir()) == []


def test_validated_video_is_atomically_published(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = _video_worker(source)

    class WritingWriter:
        def __init__(self, filename, *_args):
            self.path = Path(filename)
            self.path.touch()

        def isOpened(self):
            return True

        def write(self, _frame):
            self.path.write_bytes(b"VALIDATED_VIDEO")

        def release(self):
            pass

    _patch_video_runtime(monkeypatch, worker, WritingWriter)
    monkeypatch.setattr(worker, "validate_video_output", lambda _path: True)

    result = worker.process_video(output_dir)

    final_path = Path(result["output_file"])
    assert result["written_frame_count"] == 1
    assert final_path.name == "detected_input.mp4"
    assert final_path.read_bytes() == b"VALIDATED_VIDEO"
    assert worker.output_files == [str(final_path.resolve())]
    assert not any("partial" in path.name for path in output_dir.iterdir())


def test_cancel_request_keeps_progress_dialog_visible_until_finish(qapp):
    dialog = gui.DetectionProgressDialog("처리 중", 10)
    dialog.show()
    qapp.processEvents()

    dialog.request_cancel()
    qapp.processEvents()

    assert dialog.isVisible()
    assert "취소 요청됨" in dialog.label.text()
    assert not dialog.cancel_button.isEnabled()

    dialog.finish()
    qapp.processEvents()
    assert not dialog.isVisible()


def test_result_summary_uses_worker_target_snapshot(qapp, monkeypatch):
    window = gui.Ui_MainWindow()
    messages = []
    monkeypatch.setattr(
        gui.QMessageBox,
        "information",
        lambda _parent, _title, message: messages.append(message),
    )

    # The UI changes after submit, but the result describes a person-only run.
    window.radioButton_car.setChecked(True)
    window.display_results_new(
        {
            "source": gui.VIDEO_FILE_SOURCE,
            "image_count": 0,
            "detected_files": ["input.mp4"],
            "folder_status": "결과 폴더 준비됨",
            "execution_time": 1.0,
            "total_people": 2,
            "total_cars": 0,
            "output_files": [],
            "errors": [],
            "only_person": True,
            "only_car": False,
        }
    )

    assert "최대 동시 사람 탐지 수: 2명" in messages[0]
    assert "최대 동시 차량 탐지 수" not in messages[0]

    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    qapp.processEvents()
