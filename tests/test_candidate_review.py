import json

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from mypackage.candidate_review import CandidateReviewDialog
from mypackage.detection_records import load_detections, save_photo_review


@pytest.fixture
def record(tmp_path):
    Image.new('RGB', (300, 200), 'white').save(tmp_path / 'original.jpg')
    Image.new('RGB', (300, 200), 'white').save(tmp_path / 'detected.jpg')
    path = tmp_path / 'detections.json'
    document = {'schema_version': 1, 'photos': [{'id': 'p1', 'status': 'completed',
        'source': '/SD/a.jpg', 'image_size': [300, 200], 'gps': None,
        'original_file': 'original.jpg', 'detected_file': 'detected.jpg', 'warnings': [],
        'people': [{'id': 'c1', 'box': [40, 20, 60, 60], 'confidence': .7,
                    'review': 'unreviewed'},
                   {'id': 'c2', 'box': [100, 60, 120, 100], 'confidence': .8,
                    'review': 'unreviewed'}]}]}
    path.write_text(json.dumps(document))
    return path


def test_keyboard_review_is_per_candidate_and_survives_reopen(record, qt_application):
    dialog = CandidateReviewDialog(record)
    dialog.resize(560, 560)
    dialog.show()
    qt_application.processEvents()
    QTest.keyClick(dialog, Qt.Key.Key_1)
    QTest.keyClick(dialog, Qt.Key.Key_Right)
    QTest.keyClick(dialog, Qt.Key.Key_2)
    candidates = load_detections(record)['photos'][0]['people']
    assert [item['review'] for item in candidates] == ['person', 'false_positive']
    assert '저장' in dialog.save_status.text()
    assert dialog.width() == 560
    for button in dialog.review_buttons:
        assert button.geometry().right() < dialog.width()
        assert button.accessibleName()
    dialog.close()
    reopened = CandidateReviewDialog(record)
    assert reopened.entries[0][1]['review'] == 'person'
    reopened.close()


def test_save_failure_keeps_disk_and_visible_state(record, qt_application, monkeypatch):
    import mypackage.detection_records as records
    original = record.read_bytes()
    dialog = CandidateReviewDialog(record)

    def fail(*args):
        raise OSError('disk full')

    monkeypatch.setattr(records, 'write_json_file', fail)
    dialog.set_review('person')
    assert record.read_bytes() == original
    assert dialog.entries[0][1]['review'] == 'unreviewed'
    assert '실패' in dialog.save_status.text()
    dialog.close()


def test_save_reads_latest_other_candidate_state(record):
    save_photo_review(record, 'c2', 'hold')
    save_photo_review(record, 'c1', 'person')
    assert [item['review'] for item in load_detections(record)['photos'][0]['people']] == [
        'person', 'hold']
