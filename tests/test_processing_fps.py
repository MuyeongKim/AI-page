from pathlib import Path

import numpy as np
import pytest

from mypackage import gui


def test_loop_fps_includes_capture_plot_preview_and_write_without_skipping_frames(tmp_path, monkeypatch):
    elapsed = 0.0

    def advance(seconds):
        nonlocal elapsed
        elapsed += seconds

    class Capture:
        frames = 3

        def isOpened(self):
            return True

        def get(self, property_id):
            return {
                gui.cv2.CAP_PROP_FRAME_WIDTH: 32, gui.cv2.CAP_PROP_FRAME_HEIGHT: 24,
                gui.cv2.CAP_PROP_FPS: 30, gui.cv2.CAP_PROP_FRAME_COUNT: 3,
            }.get(property_id, 0)

        def read(self):
            if not self.frames:
                return False, None
            self.frames -= 1
            advance(0.020)
            return True, np.zeros((24, 32, 3), dtype=np.uint8)

        def release(self):
            pass

    class Result:
        boxes = []
        speed = {"inference": 10.0}

        def plot(self):
            advance(0.030)
            return np.zeros((24, 32, 3), dtype=np.uint8)

    writes = []

    class Writer:
        def __init__(self, path, *_args):
            Path(path).write_bytes(b"VIDEO")

        def isOpened(self):
            return True

        def write(self, frame):
            advance(0.040)
            writes.append(frame)

        def release(self):
            pass

    def model(*_args, **_kwargs):
        advance(0.010)
        return [Result()]

    overlays = []

    def draw(_image, fps_text, _people, _cars):
        advance(0.005)
        overlays.append(fps_text)

    source = tmp_path / "input.mp4"
    source.touch()
    worker = gui.DetectionWorker({"source": gui.VIDEO_FILE_SOURCE, "juso": [str(source)]})
    worker.model = model
    worker.frame_signal.connect(lambda _image: advance(0.010))
    monkeypatch.setattr(worker, "open_video_capture", lambda _path: Capture())
    monkeypatch.setattr(worker, "validate_video_output", lambda _path: True)
    monkeypatch.setattr(worker, "draw_info", draw)
    monkeypatch.setattr(gui.cv2, "VideoWriter", Writer)
    monkeypatch.setattr(gui.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(gui, "clear_torch_cache", lambda _device=None: None)
    monkeypatch.setattr(gui.time, "perf_counter", lambda: elapsed)

    result = worker.process_video(tmp_path / "output")

    assert result["status"] == "completed"
    assert result["frame_count"] == result["written_frame_count"] == len(writes) == 3
    assert overlays[0] == "Model est. FPS: 100.00\nLoop FPS (prev): N/A"
    assert overlays[1:] == ["Model est. FPS: 100.00\nLoop FPS (prev): 8.70"] * 2
    assert elapsed == pytest.approx(3 * 0.115)


def test_fps_overlay_draws_separate_legible_labels(monkeypatch):
    labels = []
    monkeypatch.setattr(gui.cv2, "putText", lambda _image, text, *args: labels.append(text))
    gui.DetectionWorker({}).draw_info(
        np.zeros((240, 320, 3), dtype=np.uint8),
        "Model est. FPS: 100.00\nLoop FPS (prev): 8.70", 2, 1,
    )
    assert labels == ["Model est. FPS: 100.00", "Loop FPS (prev): 8.70", "Person: 2", "Car: 1"]
