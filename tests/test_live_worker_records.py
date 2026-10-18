import json

import cv2
import numpy as np
import pytest

from mypackage import gui


class Capture:
    def __init__(self, frames=5):
        self.frames = frames
        self.reads = 0

    def isOpened(self):
        return True

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: 80, cv2.CAP_PROP_FRAME_HEIGHT: 60,
                cv2.CAP_PROP_FPS: 30}.get(prop, 0)

    def read(self):
        if self.reads >= self.frames:
            return False, None
        self.reads += 1
        return True, np.zeros((60, 80, 3), dtype=np.uint8)

    def release(self):
        pass


@pytest.mark.parametrize('ending', ['disconnected', 'cancelled', 'failed'])
def test_live_records_and_auto_manual_scenes_survive_terminal_states(tmp_path, monkeypatch, ending):
    worker = gui.DetectionWorker({'source': gui.CAPTURE_BOARD_SOURCE, 'juso': 0,
        'datasize': 'fake.pt', 'device': 'cpu', 'percentage': .1, 'imgsz': 1920,
        'classes_to_detect': [0, 2, 5, 7], 'live_settings': {'confirmation_frames': 2}})
    cap = Capture()
    monkeypatch.setattr(worker, 'open_video_capture', lambda _: cap)
    monkeypatch.setattr(gui, 'DETECTED_OUTPUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(gui, 'clear_torch_cache', lambda *args: None)
    monkeypatch.setattr(gui.cv2, 'destroyAllWindows', lambda: None)
    calls = []

    class Box:
        cls = np.array(0)
        conf = np.array(.9)

    class Result:
        names = {0: 'person'}
        boxes = [Box()]
        speed = {'inference': 1}

        def plot(self):
            return np.zeros((60, 80, 3), dtype=np.uint8)

    def model(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 3:
            worker.request_snapshot()
            worker.request_live_edit('live-000001', {'note': 'C3 쪽', 'review': 'hold'})
        if len(calls) == 5:
            if ending == 'cancelled':
                worker.stop()
            if ending == 'failed':
                raise RuntimeError('camera inference failed')
        return [Result()]

    monkeypatch.setattr(gui, 'YOLO', lambda _: model)
    outcomes, alerts = [], []
    worker.finished_signal.connect(outcomes.append)
    worker.live_alert_signal.connect(alerts.append)
    worker.run()
    result = outcomes[0]
    document = json.loads(open(result['live_events_path']).read())
    event = document['events'][0]
    assert result['status'] == document['status'] == ending
    assert event['termination'] == ending
    assert event['note'] == 'C3 쪽' and event['review'] == 'hold'
    assert {scene['trigger'] for scene in event['snapshots']} == {'auto', 'manual'}
    assert len(alerts) == 1
    assert cap.reads == len(calls) == 5
    assert all(call['conf'] == .1 and call['imgsz'] == 1920 for call in calls)
    assert result['output_files'] == []
    assert len(result['snapshot_files']) == 2
    assert all(cv2.imread(path) is not None for path in result['snapshot_files'])
    assert result['search_report_path']


@pytest.mark.parametrize('scene_write_failure', [False, True])
def test_manual_scene_without_people_and_scene_failure_keep_records(tmp_path, monkeypatch,
                                                                   scene_write_failure):
    worker = gui.DetectionWorker({'source': gui.CAPTURE_BOARD_SOURCE, 'juso': 0,
        'datasize': 'fake.pt', 'device': 'cpu', 'percentage': .1, 'imgsz': 640,
        'classes_to_detect': [0]})
    cap = Capture(frames=1)
    monkeypatch.setattr(worker, 'open_video_capture', lambda _: cap)
    monkeypatch.setattr(gui, 'DETECTED_OUTPUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(gui, 'clear_torch_cache', lambda *args: None)
    monkeypatch.setattr(gui.cv2, 'destroyAllWindows', lambda: None)

    class Empty:
        boxes = []
        speed = {'inference': 1}

        def plot(self):
            return np.zeros((60, 80, 3), dtype=np.uint8)

    def model(*args, **kwargs):
        worker.request_snapshot()
        return [Empty()]

    def fail(*args, **kwargs):
        raise OSError('scene disk full')

    if scene_write_failure:
        monkeypatch.setattr(gui.cv2, 'imencode', fail)
    monkeypatch.setattr(gui, 'YOLO', lambda _: model)
    results = []
    worker.finished_signal.connect(results.append)
    worker.run()
    result = results[0]
    assert result['status'] == 'disconnected'
    document = json.loads(open(result['live_events_path']).read())
    event = document['events'][0]
    assert event['kind'] == 'manual' and event['max_people'] == 0
    assert len(result['snapshot_files']) == (0 if scene_write_failure else 1)
    assert any('scene disk full' in warning for warning in result['warnings']) is scene_write_failure
