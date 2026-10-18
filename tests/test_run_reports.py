import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from mypackage import gui, run_report
from mypackage.version import CURRENT_VERSION


class PhotoResult:
    names = {0: "person"}
    boxes = type("Boxes", (), {"cls": [0]})()

    def save(self, filename):
        Path(filename).write_bytes(b"ANNOTATED")


def worker_for(tmp_path, monkeypatch, **overrides):
    parameters = {
        "source": "사진", "juso": [], "datasize": "fake.pt", "file_count": 1,
        "percentage": 0.1, "imgsz": 640, "device": "cpu",
        "classes_to_detect": [0], "only_person": True,
    }
    parameters.update(overrides)
    worker = gui.DetectionWorker(parameters)
    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", tmp_path / "detected_files")
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)
    return worker


def run_and_read(worker):
    results = []
    worker.finished_signal.connect(results.append)
    worker.run()
    assert len(results) == 1
    result = results[0]
    path = Path(result["report_path"])
    assert path.parent == Path(result["output_folder"])
    assert path.name == "run_summary.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report == {"schema_version": 1, **result}
    assert not any(path.name.endswith(".tmp") for path in path.parent.iterdir())
    return result, report


@pytest.mark.parametrize("input_kind", ["path", "list", "tuple"])
def test_photo_report_records_settings_times_inputs_and_preserved_results(
    tmp_path, monkeypatch, input_kind
):
    source = tmp_path / "사진.jpg"
    source.write_bytes(b"ORIGINAL_WITH_METADATA")
    inputs = {"path": source, "list": [source], "tuple": (source,)}[input_kind]
    worker = worker_for(tmp_path, monkeypatch, juso=inputs)
    monkeypatch.setattr(gui, "YOLO", lambda _path: lambda *_args, **_kwargs: [PhotoResult()])

    result, report = run_and_read(worker)

    assert report["app_version"] == CURRENT_VERSION
    assert report["source"] == "사진"
    assert report["inputs"] == (str(source) if input_kind == "path" else [str(source)])
    assert report["model"] == report["resolved_model_source"] == "fake.pt"
    assert report["confidence"] == 0.1
    assert report["image_size"] == 640
    assert report["device"] == "cpu"
    assert report["classes_to_detect"] == [0]
    assert report["only_person"] is True
    assert datetime.fromisoformat(report["started_at"]).tzinfo is not None
    assert datetime.fromisoformat(report["finished_at"]) >= datetime.fromisoformat(report["started_at"])
    assert report["execution_time"] >= 0
    assert report["execution_time_unit"] == "seconds"
    assert report["status"] == "completed"
    assert report["succeeded_count"] == report["total_people"] == 1
    assert report["errors"] == report["warnings"] == []
    assert Path(result["original_files"][0]).read_bytes() == source.read_bytes()
    assert Path(result["output_files"][0]).read_bytes() == b"ANNOTATED"


@pytest.mark.parametrize("status", ["partial", "failed", "cancelled"])
def test_photo_reports_keep_partial_failure_and_cancellation_outcomes(tmp_path, monkeypatch, status):
    good = tmp_path / "good.jpg"
    bad = tmp_path / "bad.jpg"
    good.touch()
    bad.touch()
    paths = [bad] if status == "failed" else [good, bad]
    worker = worker_for(tmp_path, monkeypatch, juso=paths, file_count=len(paths))

    def model(path, **_kwargs):
        if Path(path) == bad:
            raise RuntimeError("unreadable input")
        return [PhotoResult()]

    monkeypatch.setattr(gui, "YOLO", lambda _path: model)
    if status == "cancelled":
        attempt = worker.process_image_attempt

        def process_then_cancel(*args):
            attempt(*args)
            worker.stop()

        monkeypatch.setattr(worker, "process_image_attempt", process_then_cancel)

    result, report = run_and_read(worker)

    assert report["status"] == status
    if status == "cancelled":
        assert report["attempted_count"] == report["succeeded_count"] == 1
    else:
        assert report["failed_count"] == 1
        assert "unreadable input" in report["errors"][0]
    assert all(Path(path).is_file() for path in result["output_files"])


class VideoCapture:
    def __init__(self, reported_frames):
        self.frames_left = 3
        self.reported_frames = reported_frames

    def isOpened(self):
        return True

    def get(self, property_id):
        return {
            cv2.CAP_PROP_FRAME_WIDTH: 32, cv2.CAP_PROP_FRAME_HEIGHT: 24,
            cv2.CAP_PROP_FPS: 5, cv2.CAP_PROP_FRAME_COUNT: self.reported_frames,
        }.get(property_id, 0)

    def read(self):
        if not self.frames_left:
            return False, None
        self.frames_left -= 1
        return True, np.zeros((24, 32, 3), dtype=np.uint8)

    def release(self):
        pass


class VideoResult:
    boxes = []
    speed = {"inference": 10.0}

    def plot(self):
        return np.zeros((24, 32, 3), dtype=np.uint8)


@pytest.mark.parametrize("status", ["completed", "partial", "failed", "cancelled", "disconnected"])
def test_video_report_tracks_written_frames_and_only_preserved_outputs(tmp_path, monkeypatch, status):
    source = tmp_path / "input.mp4"
    source.touch()
    live = status == "disconnected"
    worker = worker_for(
        tmp_path, monkeypatch,
        source=gui.CAPTURE_BOARD_SOURCE if live else gui.VIDEO_FILE_SOURCE,
        juso=0 if live else [source],
    )
    capture = VideoCapture(10 if status == "partial" else 3)
    monkeypatch.setattr(worker, "open_video_capture", lambda _source: capture)
    calls = 0

    def model(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if status == "failed" and calls == 2:
            raise RuntimeError("inference failed")
        if status == "cancelled":
            worker.stop()
        return [VideoResult()]

    monkeypatch.setattr(gui, "YOLO", lambda _path: model)
    result, report = run_and_read(worker)

    assert report["status"] == status
    assert report["video_frame_count"] == (1 if status in {"failed", "cancelled"} else 3)
    assert report["written_frame_count"] == (0 if live else report["video_frame_count"])
    assert len(result["output_files"]) == (1 if status in {"completed", "partial"} else 0)
    assert all(Path(path).is_file() for path in result["output_files"])
    assert bool(report["warnings"]) is (status == "partial")
    assert bool(report["errors"]) is (status in {"failed", "disconnected"})


def test_report_failure_warns_without_changing_detection_or_removing_results(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"ORIGINAL")
    worker = worker_for(tmp_path, monkeypatch, juso=[source])
    monkeypatch.setattr(gui, "YOLO", lambda _path: lambda *_args, **_kwargs: [PhotoResult()])

    def fail_report(*_args):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(gui, "write_run_report", fail_report)
    results = []
    worker.finished_signal.connect(results.append)
    worker.run()
    [result] = results

    assert result["status"] == "completed"
    assert result["report_path"] is None
    assert result["report_warning"] in result["warnings"]
    assert "No space left" in result["report_warning"]
    assert result["errors"] == []
    assert Path(result["original_files"][0]).read_bytes() == b"ORIGINAL"
    assert Path(result["output_files"][0]).is_file()


@pytest.mark.parametrize("failure_step", ["serialization", "publish"])
def test_atomic_report_failure_keeps_previous_report_and_cleans_temporary_files(
    tmp_path, monkeypatch, failure_step
):
    previous = tmp_path / "run_summary.json"
    previous.write_bytes(b"PREVIOUS_REPORT")

    def fail_publish(*_args):
        raise OSError("replace failed")

    if failure_step == "publish":
        monkeypatch.setattr(run_report.os, "replace", fail_publish)
        report = {"status": "completed"}
    else:
        report = {"not_json": object()}
    with pytest.raises((TypeError, OSError)):
        run_report.write_run_report(tmp_path, report)

    assert previous.read_bytes() == b"PREVIOUS_REPORT"
    assert list(tmp_path.iterdir()) == [previous]


def test_model_load_failure_keeps_the_existing_no_run_folder_policy(tmp_path, monkeypatch):
    worker = worker_for(tmp_path, monkeypatch)

    def fail_model(_path):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(gui, "YOLO", fail_model)
    results = []
    worker.finished_signal.connect(results.append)
    worker.run()

    assert results[0]["status"] == "failed"
    assert results[0]["output_folder"] is results[0]["report_path"] is None
    assert not (tmp_path / "detected_files").exists()
