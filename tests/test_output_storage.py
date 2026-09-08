import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QLockFile

from mypackage import gui, output_storage


class _PhotoResult:
    def __init__(self, content=b"CURRENT_RESULT"):
        self.content = content

    def save(self, filename):
        Path(filename).write_bytes(self.content)


def test_run_folders_use_start_time_and_preserve_occupied_names(tmp_path):
    started_at = output_storage.time.mktime((2026, 9, 8, 14, 30, 25, 0, 0, -1))
    occupied = tmp_path / "20260908_143025"
    occupied.mkdir()
    previous = occupied / "previous.jpg"
    previous.write_bytes(b"PREVIOUS")
    occupied_file = tmp_path / "20260908_143025_1"
    occupied_file.write_bytes(b"OCCUPIED")

    folder = output_storage.create_run_output_folder(tmp_path, started_at=started_at)

    assert folder == tmp_path / "20260908_143025_2"
    assert folder.is_dir()
    assert previous.read_bytes() == b"PREVIOUS"
    assert occupied_file.read_bytes() == b"OCCUPIED"


def test_concurrent_runs_allocate_separate_folders(tmp_path):
    def allocate(_index):
        return output_storage.create_run_output_folder(tmp_path / "results", started_at=0)

    with ThreadPoolExecutor(max_workers=8) as pool:
        folders = list(pool.map(allocate, range(16)))

    assert len(set(folders)) == 16
    assert all(folder.is_dir() and folder.parent == tmp_path / "results" for folder in folders)


@pytest.mark.parametrize("source_type", ["사진", gui.VIDEO_FILE_SOURCE])
def test_each_detection_run_saves_into_its_own_reported_folder(
    tmp_path, monkeypatch, source_type
):
    source = tmp_path / ("source.jpg" if source_type == "사진" else "source.mp4")
    source.write_bytes(b"ORIGINAL")
    root = tmp_path / "detected_files"
    root.mkdir()
    previous = root / "previous.jpg"
    previous.write_bytes(b"PREVIOUS")
    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", root)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)

    class PhotoResult(_PhotoResult):
        def __init__(self):
            super().__init__()
            self.names = {0: "person"}
            self.boxes = type("Boxes", (), {"cls": [0]})()

    monkeypatch.setattr(gui, "YOLO", lambda _source: lambda *_args, **_kwargs: [PhotoResult()])
    results = []
    for _ in range(2):
        worker = gui.DetectionWorker(
            {"source": source_type, "juso": [str(source)], "datasize": "fake.pt", "file_count": 1}
        )
        if source_type == gui.VIDEO_FILE_SOURCE:
            def process_video(folder, worker=worker):
                output = Path(folder) / "detected_source.mp4"
                output.write_bytes(b"VIDEO")
                worker.output_files.append(str(output))
                return {"had_detection": True, "source": str(source), "status": "completed"}

            monkeypatch.setattr(worker, "process_video", process_video)
        worker.finished_signal.connect(results.append)
        worker.run()

    folders = [Path(result["output_folder"]) for result in results]
    assert all(result["status"] == "completed" for result in results)
    assert folders[0] != folders[1]
    assert all(folder.parent == root for folder in folders)
    for result, folder in zip(results, folders):
        assert str(folder) in result["folder_status"]
        assert all(Path(path).parent == folder for path in result["output_files"])
        assert Path(result["output_files"][0]).stem == "detected_source"
        if source_type == "사진":
            assert Path(result["original_files"][0]).parent == folder
            assert Path(result["original_files"][0]).read_bytes() == b"ORIGINAL"
    assert previous.read_bytes() == b"PREVIOUS"


def test_uncreatable_run_folder_emits_failure_without_exposing_previous_results(
    tmp_path, monkeypatch
):
    root = tmp_path / "not_a_folder"
    root.write_bytes(b"PREVIOUS")
    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", root)
    monkeypatch.setattr(gui, "YOLO", lambda _source: object())
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    worker = gui.DetectionWorker({"source": "사진", "juso": [], "datasize": "fake.pt"})
    results = []
    worker.finished_signal.connect(results.append)

    worker.run()

    assert results[0]["status"] == "failed"
    assert results[0]["output_folder"] is None
    assert results[0]["errors"]
    assert root.read_bytes() == b"PREVIOUS"


def test_failed_original_copy_leaves_no_final_or_partial_file(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"COMPLETE_ORIGINAL")
    folder = tmp_path / "output"

    def fail_after_partial_copy(_source, destination):
        Path(destination).write_bytes(b"TRUNCATED")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(gui.shutil, "copy2", fail_after_partial_copy)
    with pytest.raises(OSError, match="No space left"):
        gui.DetectionWorker({}).file_copy(source, _PhotoResult(), folder)

    assert source.read_bytes() == b"COMPLETE_ORIGINAL"
    assert list(folder.iterdir()) == []


def test_photo_pair_uses_matching_suffix_across_source_extensions(tmp_path):
    folder = tmp_path / "output"
    worker = gui.DetectionWorker({})
    for index, extension in enumerate(["jpg", "png", "jpg"]):
        source = tmp_path / f"same.{extension}"
        source.write_bytes(f"SOURCE_{index}".encode())
        original, detected = worker.file_copy(source, _PhotoResult(), folder)
        suffix = f"_{index}" if index else ""
        assert Path(original).name == f"original_same{suffix}.{extension}"
        assert Path(detected).name == f"detected_same{suffix}.jpg"
        assert Path(original).read_bytes() == f"SOURCE_{index}".encode()
    assert len(list(folder.iterdir())) == 6


def test_cancel_after_original_staging_removes_both_temporary_files(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"ORIGINAL")
    folder = tmp_path / "output"
    worker = gui.DetectionWorker({})
    copy = gui.shutil.copy2

    def copy_then_cancel(source, destination):
        copy(source, destination)
        worker.stop()

    monkeypatch.setattr(gui.shutil, "copy2", copy_then_cancel)
    with pytest.raises(RuntimeError, match="취소 요청"):
        worker.file_copy(source, _PhotoResult(), folder)
    assert list(folder.iterdir()) == []
    assert source.read_bytes() == b"ORIGINAL"


def test_failed_second_publication_rolls_back_pair_and_releases_lock(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"ORIGINAL")
    folder = tmp_path / "output"
    folder.mkdir()
    previous = folder / "original_source.jpg"
    previous.write_bytes(b"PREVIOUS")
    replace = output_storage.os.replace

    def fail_annotated_publication(staged, destination):
        if Path(destination).name.startswith("detected_"):
            raise OSError("publication failed")
        return replace(staged, destination)

    with monkeypatch.context() as patch:
        patch.setattr(output_storage.os, "replace", fail_annotated_publication)
        with pytest.raises(OSError, match="publication failed"):
            gui.DetectionWorker({}).file_copy(source, _PhotoResult(), folder)

    assert list(folder.iterdir()) == [previous]
    assert previous.read_bytes() == b"PREVIOUS"
    original, detected = gui.DetectionWorker({}).file_copy(source, _PhotoResult(), folder)
    assert Path(original).name == "original_source_1.jpg"
    assert Path(detected).name == "detected_source_1.jpg"


def test_cancel_while_waiting_for_publication_lock_preserves_other_owner(tmp_path):
    staged = tmp_path / ".partial.mp4"
    staged.write_bytes(b"RESULT")
    held_lock = QLockFile(str(tmp_path / ".output-publish.lock"))
    assert held_lock.tryLock(0)
    cancellation_checks = 0

    def cancel_after_first_wait():
        nonlocal cancellation_checks
        cancellation_checks += 1
        return cancellation_checks > 1

    try:
        with pytest.raises(RuntimeError, match="취소 요청"):
            output_storage.publish_output_files(
                [staged], ["detected_source.mp4"], is_cancelled=cancel_after_first_wait
            )
        assert held_lock.isLocked()
        assert staged.read_bytes() == b"RESULT"
        assert not (tmp_path / "detected_source.mp4").exists()
    finally:
        held_lock.unlock()


def test_dead_process_publication_lock_is_recovered(tmp_path):
    script = """
import sys
from PySide6.QtCore import QLockFile
lock = QLockFile(sys.argv[1])
lock.setStaleLockTime(0)
assert lock.tryLock(0)
print('ready', flush=True)
sys.stdin.readline()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path / ".output-publish.lock")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout.readline().strip() == "ready"
    finally:
        process.kill()
        process.communicate(timeout=10)
    staged = tmp_path / ".partial.mp4"
    staged.write_bytes(b"COMPLETE")
    [output] = output_storage.publish_output_files([staged], ["detected_source.mp4"])
    assert output.read_bytes() == b"COMPLETE"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize(
    "names",
    [
        ["original_same.jpg", "detected_same.jpg"],
        ["detected_same.mp4"],
    ],
)
def test_separate_processes_never_overwrite_completed_outputs(tmp_path, names):
    script = """
import json, sys, time
from pathlib import Path
from mypackage import output_storage
folder, tag, encoded_names = sys.argv[1:]
folder = Path(folder)
names = json.loads(encoded_names)
staged = []
for index, name in enumerate(names):
    path = folder / ('.' + tag + '-' + name)
    path.write_bytes((tag + '-' + str(index)).encode())
    staged.append(path)
replace = output_storage.os.replace
def slow_replace(source, destination):
    # Widen the original name-check/rename race in both independent processes.
    time.sleep(0.2)
    return replace(source, destination)
output_storage.os.replace = slow_replace
print('ready', flush=True)
sys.stdin.readline()
published = output_storage.publish_output_files(staged, names)
print(json.dumps([str(path) for path in published]), flush=True)
"""
    processes = []
    results = []
    try:
        for tag in ["A", "B"]:
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-c", script, str(tmp_path), tag, json.dumps(names)],
                    cwd=Path(__file__).resolve().parent.parent,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        for process in processes:
            assert process.stdout.readline().strip() == "ready"
        for process in processes:
            process.stdin.write("\n")
            process.stdin.flush()
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, stderr
            results.append(json.loads(stdout))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    assert set(results[0]).isdisjoint(results[1])
    for tag, paths in zip(["A", "B"], results):
        for index, path in enumerate(paths):
            assert Path(path).read_bytes() == f"{tag}-{index}".encode()
    assert len(list(tmp_path.iterdir())) == 2 * len(names)


def test_worker_emits_model_and_photo_stages_without_breaking_legacy_progress(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.jpg"
    source.touch()

    class EmptyResult:
        names = {}
        boxes = None

    worker = gui.DetectionWorker(
        {"source": "사진", "juso": [str(source)], "datasize": "fake.pt", "file_count": 1}
    )
    stages = []
    legacy_progress = []
    worker.stage_signal.connect(lambda message, current, total: stages.append((message, current, total)))
    worker.progress_signal.connect(lambda current, message: legacy_progress.append((current, message)))
    monkeypatch.setattr(gui, "DETECTED_OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(gui, "YOLO", lambda _model: lambda *_args, **_kwargs: [EmptyResult()])
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)

    worker.run()

    assert stages[0] == ("모델 준비 중: fake.pt", 0, 0)
    assert ("사진 분석 중", 0, 1) in stages
    assert stages[-1] == ("사진 분석 중", 1, 1)
    assert legacy_progress == [(1, "진행 중... 1 / 1")]


def test_video_stages_cover_analysis_and_full_output_verification(tmp_path, monkeypatch):
    source = tmp_path / "short.mp4"
    frame = np.zeros((24, 32, 3), dtype=np.uint8)
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5, (32, 24))
    assert writer.isOpened()
    for _ in range(3):
        writer.write(frame)
    writer.release()

    class VideoResult:
        boxes = []
        names = {}
        speed = {"inference": 1.0}

        def plot(self):
            return frame.copy()

    worker = gui.DetectionWorker({"source": gui.VIDEO_FILE_SOURCE, "juso": [str(source)]})
    worker.model = lambda *_args, **_kwargs: [VideoResult()]
    stages = []
    worker.stage_signal.connect(lambda message, current, total: stages.append((message, current, total)))
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)

    result = worker.process_video(tmp_path / "output")

    assert result["status"] == gui.DETECTION_STATUS_COMPLETED
    assert ("영상 분석 중", 0, 3) in stages
    assert ("영상 분석 중", 3, 3) in stages
    assert ("결과 영상 전체 검증 중", 0, 3) in stages
    assert ("결과 영상 전체 검증 중", 3, 3) in stages
    assert stages.index(("영상 분석 중", 3, 3)) < stages.index(("결과 영상 전체 검증 중", 0, 3))
    assert stages[-1] == ("검증한 결과 영상 저장 중", 0, 0)
