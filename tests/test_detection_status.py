import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from mypackage import gui


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


class _EmptyPhotoResult:
    names = {}
    boxes = None


class _SelectivePhotoModel:
    def __call__(self, source, **_kwargs):
        if Path(source).name.startswith("bad"):
            raise RuntimeError("mock inference failure")
        return [_EmptyPhotoResult()]


def _run_worker(worker, tmp_path, monkeypatch, model):
    results = []
    fatal_errors = []
    worker.finished_signal.connect(results.append)
    worker.error_signal.connect(fatal_errors.append)
    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", tmp_path / "detected")
    monkeypatch.setattr(gui, "YOLO", lambda _source: model)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    worker.run()
    return results, fatal_errors


def test_photo_partial_status_distinguishes_attempt_success_and_failure(tmp_path, monkeypatch):
    good = tmp_path / "good.jpg"
    bad = tmp_path / "bad.jpg"
    good.touch()
    bad.touch()
    worker = gui.DetectionWorker(_worker_params(juso=[str(good), str(bad)], file_count=2))

    results, fatal_errors = _run_worker(worker, tmp_path, monkeypatch, _SelectivePhotoModel())

    assert fatal_errors == []
    assert len(results) == 1
    assert results[0]["status"] == gui.DETECTION_STATUS_PARTIAL
    assert results[0]["processed_count"] == 2
    assert results[0]["attempted_count"] == 2
    assert results[0]["succeeded_count"] == 1
    assert results[0]["failed_count"] == 1
    assert len(results[0]["errors"]) == 1


def test_all_photo_failures_emit_failed_structured_result_without_fatal_signal(
    tmp_path, monkeypatch
):
    bad_files = [tmp_path / "bad-1.jpg", tmp_path / "bad-2.jpg"]
    for path in bad_files:
        path.touch()
    worker = gui.DetectionWorker(
        _worker_params(juso=[str(path) for path in bad_files], file_count=2)
    )

    results, fatal_errors = _run_worker(worker, tmp_path, monkeypatch, _SelectivePhotoModel())

    assert fatal_errors == []
    assert len(results) == 1
    assert results[0]["status"] == gui.DETECTION_STATUS_FAILED
    assert results[0]["attempted_count"] == 2
    assert results[0]["succeeded_count"] == 0
    assert results[0]["failed_count"] == 2
    assert len(results[0]["errors"]) == 2


def test_fatal_model_error_keeps_error_signal_and_also_emits_failed_result(tmp_path, monkeypatch):
    worker = gui.DetectionWorker(_worker_params())
    results = []
    fatal_errors = []
    worker.finished_signal.connect(results.append)
    worker.error_signal.connect(fatal_errors.append)

    def fail_model_load(_source):
        raise RuntimeError("model load failed")

    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", tmp_path / "detected")
    monkeypatch.setattr(gui, "YOLO", fail_model_load)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    worker.run()

    assert fatal_errors == ["model load failed"]
    assert len(results) == 1
    assert results[0]["status"] == gui.DETECTION_STATUS_FAILED
    assert results[0]["fatal_error"] == "model load failed"
    assert results[0]["errors"] == ["model load failed"]


def test_fatal_error_after_successful_photo_is_partial(tmp_path, monkeypatch):
    image = tmp_path / "good.jpg"
    image.touch()
    worker = gui.DetectionWorker(_worker_params(juso=[str(image)], file_count=2))

    def process_one_then_fail(_output_folder, _detected_files):
        worker.attempted_count = 1
        worker.succeeded_count = 1
        worker.processed_count = 1
        raise RuntimeError("folder iteration failed")

    monkeypatch.setattr(worker, "process_images", process_one_then_fail)
    results, fatal_errors = _run_worker(worker, tmp_path, monkeypatch, object())

    assert fatal_errors == ["folder iteration failed"]
    assert results[0]["status"] == gui.DETECTION_STATUS_PARTIAL
    assert results[0]["succeeded_count"] == 1
    assert results[0]["fatal_error"] == "folder iteration failed"


class _Capture:
    def __init__(
        self,
        cv2_module,
        frames,
        expected_frames=0,
        before_eof=None,
        fps=30.0,
        position_ms=0.0,
    ):
        self.cv2 = cv2_module
        self.frames = iter(frames)
        self.expected_frames = expected_frames
        self.before_eof = before_eof
        self.fps = fps
        self.position_ms = position_ms
        self.released = False

    def isOpened(self):
        return True

    def get(self, property_id):
        if property_id == self.cv2.CAP_PROP_FRAME_WIDTH:
            return 8
        if property_id == self.cv2.CAP_PROP_FRAME_HEIGHT:
            return 8
        if property_id == self.cv2.CAP_PROP_FPS:
            return self.fps
        if property_id == self.cv2.CAP_PROP_FRAME_COUNT:
            return self.expected_frames
        if property_id == self.cv2.CAP_PROP_POS_MSEC:
            return self.position_ms
        return 0

    def read(self):
        try:
            return True, next(self.frames)
        except StopIteration:
            if self.before_eof is not None:
                self.before_eof()
            return False, None

    def release(self):
        self.released = True


class _VideoResult:
    boxes = []
    names = {}
    speed = {"inference": 1.0}

    def plot(self):
        return np.zeros((8, 8, 3), dtype=np.uint8)


class _FailAfterOneFrameModel:
    def __init__(self):
        self.call_count = 0

    def __call__(self, *_args, **_kwargs):
        self.call_count += 1
        if self.call_count > 1:
            raise RuntimeError("second frame inference failed")
        return [_VideoResult()]


class _WritingWriter:
    def __init__(self, filename, *_args):
        self.path = Path(filename)
        self.path.touch()

    def isOpened(self):
        return True

    def write(self, _frame):
        self.path.write_bytes(b"partial output")

    def release(self):
        pass


def _patch_video_runtime(monkeypatch, worker, capture):
    monkeypatch.setattr(worker, "open_video_capture", lambda _source: capture)
    monkeypatch.setattr(gui.cv2, "VideoWriter", _WritingWriter)
    monkeypatch.setattr(gui.cv2, "VideoWriter_fourcc", lambda *_args: 0)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)


def test_container_frame_count_mismatch_is_advisory(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = gui.DetectionWorker(
        _worker_params(
            source=gui.VIDEO_FILE_SOURCE,
            juso=[str(source)],
            file_count=1,
        )
    )
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    capture = _Capture(
        gui.cv2,
        [np.zeros((8, 8, 3), dtype=np.uint8)],
        expected_frames=55,
        fps=10.0,
        position_ms=5_400.0,
    )
    _patch_video_runtime(monkeypatch, worker, capture)
    monkeypatch.setattr(worker, "validate_video_output", lambda _path: True)

    result = worker.process_video(output_dir)

    assert capture.released is True
    assert result["status"] == gui.DETECTION_STATUS_COMPLETED
    assert result["frame_count"] == 1
    assert result["reported_frame_count"] == 55
    assert worker.video_frame_count == 1
    assert worker.reported_video_frame_count == 55
    assert len(worker.warnings) == 1
    assert "보고 55프레임" in worker.warnings[0]
    assert len(worker.output_files) == 1
    assert Path(worker.output_files[0]).is_file()


def test_video_ending_far_before_reported_duration_is_partial(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = gui.DetectionWorker(
        _worker_params(
            source=gui.VIDEO_FILE_SOURCE,
            juso=[str(source)],
            file_count=1,
        )
    )
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    capture = _Capture(
        gui.cv2,
        [np.zeros((8, 8, 3), dtype=np.uint8)],
        expected_frames=10,
    )
    _patch_video_runtime(monkeypatch, worker, capture)
    monkeypatch.setattr(worker, "validate_video_output", lambda _path: True)

    result = worker.process_video(output_dir)

    assert result["status"] == gui.DETECTION_STATUS_PARTIAL
    assert result["frame_count"] == 1
    assert result["reported_frame_count"] == 10
    assert worker.errors == []
    assert len(worker.warnings) == 1
    assert "부분 완료로 보존합니다" in worker.warnings[0]
    assert len(worker.output_files) == 1
    assert Path(worker.output_files[0]).is_file()
    assert result["output_file"] == worker.output_files[0]


def test_vfr_timing_can_reach_reported_end_despite_frame_count_mismatch():
    assert gui.DetectionWorker.video_reached_reported_end(55, 10.0, 5_400.0)
    assert not gui.DetectionWorker.video_reached_reported_end(100, 30.0, 0.0)


def test_video_output_validation_decodes_all_expected_frames(tmp_path, monkeypatch):
    output = tmp_path / "result.mp4"
    output.write_bytes(b"non-empty")
    worker = gui.DetectionWorker(_worker_params())
    worker._video_output_expected_frames = 3
    verification_capture = _Capture(
        gui.cv2,
        [
            np.zeros((8, 8, 3), dtype=np.uint8),
            np.zeros((8, 8, 3), dtype=np.uint8),
        ],
    )
    monkeypatch.setattr(gui.cv2, "VideoCapture", lambda _path: verification_capture)

    assert worker.validate_video_output(output) is False
    assert verification_capture.released is True


def test_capture_board_read_failure_is_disconnected(tmp_path, monkeypatch):
    worker = gui.DetectionWorker(_worker_params(source=gui.CAPTURE_BOARD_SOURCE, juso=0))
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    capture = _Capture(
        gui.cv2,
        [np.zeros((8, 8, 3), dtype=np.uint8)],
    )
    _patch_video_runtime(monkeypatch, worker, capture)

    result = worker.process_video(tmp_path / "detected")

    assert result["status"] == gui.DETECTION_STATUS_DISCONNECTED
    assert result["frame_count"] == 1
    assert len(worker.errors) == 1


def test_capture_board_user_cancel_wins_over_read_failure(tmp_path, monkeypatch):
    worker = gui.DetectionWorker(_worker_params(source=gui.CAPTURE_BOARD_SOURCE, juso=0))
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    capture = _Capture(gui.cv2, [], before_eof=worker.stop)
    _patch_video_runtime(monkeypatch, worker, capture)

    result = worker.process_video(tmp_path / "detected")

    assert result["status"] == gui.DETECTION_STATUS_CANCELLED
    assert worker.errors == []


def test_video_failure_preserves_completed_frame_progress(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    worker = gui.DetectionWorker(
        _worker_params(
            source=gui.VIDEO_FILE_SOURCE,
            juso=[str(source)],
            file_count=1,
        )
    )
    worker.model = _FailAfterOneFrameModel()
    capture = _Capture(
        gui.cv2,
        [
            np.zeros((8, 8, 3), dtype=np.uint8),
            np.zeros((8, 8, 3), dtype=np.uint8),
        ],
        expected_frames=2,
    )
    _patch_video_runtime(monkeypatch, worker, capture)

    try:
        worker.process_video(tmp_path / "detected")
    except RuntimeError as exc:
        assert "second frame inference failed" in str(exc)
    else:
        raise AssertionError("영상 추론 오류가 실패로 전파되지 않음")

    assert worker.processed_count == 1
    assert worker.video_frame_count == 1
    assert worker.written_frame_count == 1


def test_cancel_during_output_validation_prevents_publish(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "detected"
    worker = gui.DetectionWorker(
        _worker_params(
            source=gui.VIDEO_FILE_SOURCE,
            juso=[str(source)],
            file_count=1,
        )
    )
    worker.model = lambda *_args, **_kwargs: [_VideoResult()]
    source_capture = _Capture(
        gui.cv2,
        [np.zeros((8, 8, 3), dtype=np.uint8)],
        expected_frames=1,
    )
    validation_capture = _Capture(
        gui.cv2,
        [np.zeros((8, 8, 3), dtype=np.uint8)],
    )
    original_read = validation_capture.read

    def stop_on_first_validation_frame():
        result = original_read()
        worker.stop()
        return result

    validation_capture.read = stop_on_first_validation_frame
    _patch_video_runtime(monkeypatch, worker, source_capture)
    monkeypatch.setattr(gui.cv2, "VideoCapture", lambda _path: validation_capture)

    result = worker.process_video(output_dir)

    assert result["status"] == gui.DETECTION_STATUS_CANCELLED
    assert result["output_file"] is None
    assert worker.output_files == []
    assert list(output_dir.iterdir()) == []
