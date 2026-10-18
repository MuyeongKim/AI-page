import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from mypackage import gui
from mypackage.detection_records import load_detections, read_photo_metadata


class Result:
    names = {0: 'person', 2: 'car'}
    orig_shape = (120, 160)
    boxes = type('Boxes', (), {'cls': np.array([0, 0, 2]),
                              'xyxy': np.array([[1, 2, 20, 60], [70, 30, 90, 80], [0, 0, 20, 20]]),
                              'conf': np.array([.6, .8, .9])})()

    def save(self, filename):
        cv2.imwrite(filename, np.zeros((120, 160, 3), dtype=np.uint8))


def test_photo_records_preserve_individual_candidates_empty_and_failed_inputs(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ('people.jpg', 'empty.jpg', 'bad.jpg')]
    for path in paths:
        cv2.imwrite(str(path), np.zeros((120, 160, 3), dtype=np.uint8))
    calls = []

    def model(path, **kwargs):
        calls.append(kwargs)
        if Path(path).name == 'bad.jpg':
            raise ValueError('bad image')
        result = Result()
        if Path(path).name == 'empty.jpg':
            result.boxes = type('Boxes', (), {'cls': [], 'xyxy': [], 'conf': []})()
        return [result]

    monkeypatch.setattr(gui, 'YOLO', lambda _: model)
    monkeypatch.setattr(gui, 'DETECTED_OUTPUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(gui, 'clear_torch_cache', lambda *args: None)
    worker = gui.DetectionWorker({'source': '사진', 'juso': paths, 'datasize': 'fake.pt',
                                  'classes_to_detect': [0, 2, 5, 7], 'percentage': .1,
                                  'imgsz': 1920, 'device': 'cpu', 'file_count': 3})
    outcomes = []
    worker.finished_signal.connect(outcomes.append)
    worker.run()
    result = outcomes[0]
    document = load_detections(result['detections_path'])
    people, empty, failed = document['photos']
    assert document['status'] == 'partial'
    assert people['image_size'] == [160, 120]
    assert len(people['people']) == 2
    assert people['people'][0]['id'] != people['people'][1]['id']
    assert people['people'][0]['review'] == 'unreviewed'
    assert people['people'][1]['confidence'] == pytest.approx(.8)
    assert people['vehicles'] == 1
    assert people['location_kind'] == 'photo_gps'
    assert people['gps'] is None
    assert empty['people'] == [] and empty['original_file'] is None
    assert failed['status'] == 'failed' and 'bad image' in failed['error']
    assert all(call['conf'] == .1 and call['imgsz'] == 1920 and
               call['classes'] == [0, 2, 5, 7] for call in calls)
    assert not list(Path(result['output_folder']).glob('*.tmp'))


def test_metadata_offset_is_kept_and_bad_gps_does_not_drop_photo(tmp_path, monkeypatch):
    import mypackage.detection_records as records
    photo = tmp_path / 'photo.jpg'
    photo.touch()
    monkeypatch.setattr(records.exifread, 'process_file', lambda *args, **kwargs: {
        'EXIF DateTimeOriginal': '2026:10:18 12:30:00', 'EXIF OffsetTimeOriginal': '+09:00'})
    monkeypatch.setattr(records.gps2, 'extract_gps_data', lambda _: (float('nan'), 127))
    metadata = read_photo_metadata(photo)
    assert metadata['captured_at'] == '2026-10-18T12:30:00+09:00'
    assert metadata['gps'] is None and metadata['warnings']


def test_loader_rejects_invalid_coordinates_and_escaping_assets(tmp_path):
    path = tmp_path / 'detections.json'
    base = {'schema_version': 1, 'photos': [{'id': 'p1', 'status': 'completed',
        'image_size': [100, 100], 'original_file': '../outside.jpg', 'detected_file': None,
        'people': [], 'gps': None}]}
    path.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        load_detections(path)
    base['photos'][0]['original_file'] = None
    base['photos'][0]['people'] = [{'id': 'c1', 'confidence': .7,
                                    'box': [0, 0, float('inf'), 10], 'review': 'unreviewed'}]
    path.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        load_detections(path)
