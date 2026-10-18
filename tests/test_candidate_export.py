import copy
import json
import shutil

import pytest
from PIL import Image

from mypackage.candidate_export import export_photo_candidates
from mypackage.detection_records import save_photo_review


@pytest.fixture
def photo_record(tmp_path):
    Image.new('RGB', (200, 120), 'green').save(tmp_path / 'thumb.jpg')
    photo = {'id': 'p1', 'status': 'completed', 'source': '/private/SD/photo.jpg',
             'original_file': None, 'detected_file': None, 'gps': {'lat': 35., 'lon': 127.},
             'captured_at': '2026-10-18T12:00:00', 'image_size': [200, 120],
             'people': [{'id': 'p1-person-1', 'confidence': .7, 'box': [1, 2, 20, 30],
                         'review': 'unreviewed', 'thumbnail_file': 'thumb.jpg'}]}
    document = {'schema_version': 1, 'status': 'partial', 'photos': [photo]}
    second = copy.deepcopy(photo)
    second.update(id='p2', source='C:\\SD\\other.jpg', gps=None, captured_at=None)
    second['people'][0].update(id='p2-person-1', thumbnail_file=None)
    document['photos'].append(second)
    path = tmp_path / 'detections.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    return path


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_portable_export_has_only_photo_location_and_embedded_small_preview(photo_record):
    destination = photo_record.parent / 'stayup-ai-candidates.json'
    export_photo_candidates(photo_record, destination)
    payload = read(destination)
    assert payload['format'] == 'stayup-ai-candidates' and payload['version'] == 1
    assert payload['app']['version'] == '26.1018'
    assert payload['run']['revision'] == 1 and payload['run']['photoCount'] == 2
    first, second = payload['candidates']
    assert first['file'] == 'photo.jpg' and second['file'] == 'other.jpg'
    assert first['thumbnail'].startswith('data:image/jpeg;base64,')
    assert len(first['thumbnail']) < 45000 and second['thumbnail'] is None
    assert first['gps'] == {'lat': 35., 'lon': 127.} and second['gps'] is None
    assert first['locationKind'] == 'photo_gps'
    assert first['capturedAt'] == '2026-10-18T12:00:00'
    assert '/private/' not in destination.read_text(encoding='utf-8')


def test_repeat_copy_and_review_update_keep_identity_and_advance_revision(photo_record, tmp_path):
    destination = tmp_path / 'export.json'
    export_photo_candidates(photo_record, destination)
    before = read(destination)
    export_photo_candidates(photo_record, destination)
    assert read(destination)['run'] == before['run']
    moved = tmp_path / 'moved'
    moved.mkdir()
    shutil.copy2(photo_record, moved / photo_record.name)
    shutil.copy2(tmp_path / 'thumb.jpg', moved / 'thumb.jpg')
    save_photo_review(moved / photo_record.name, 'p1-person-1', 'hold')
    export_photo_candidates(moved / photo_record.name, destination)
    after = read(destination)
    assert after['run']['id'] == before['run']['id']
    assert after['run']['revision'] == 2
    assert after['candidates'][0]['review'] == 'hold'


def test_failed_write_preserves_previous_export_and_retry_revision(photo_record, monkeypatch):
    import mypackage.candidate_export as exporter
    destination = photo_record.parent / 'export.json'
    export_photo_candidates(photo_record, destination)
    before = destination.read_bytes()
    save_photo_review(photo_record, 'p1-person-1', 'person')
    write = exporter.write_json_file

    def fail_output(path, document):
        if path == destination:
            raise OSError('disk full')
        return write(path, document)

    monkeypatch.setattr(exporter, 'write_json_file', fail_output)
    with pytest.raises(OSError, match='disk full'):
        export_photo_candidates(photo_record, destination)
    assert destination.read_bytes() == before
    monkeypatch.setattr(exporter, 'write_json_file', write)
    export_photo_candidates(photo_record, destination)
    assert read(destination)['run']['revision'] == 2


@pytest.mark.parametrize('target', ['detections.json', 'thumb.jpg', 'run_summary.json'])
def test_cannot_overwrite_source_or_a_referenced_asset(photo_record, target):
    path = photo_record.parent / target
    if not path.exists():
        path.write_text('{}', encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(ValueError):
        export_photo_candidates(photo_record, path)
    assert path.read_bytes() == before


def test_running_or_corrupt_record_cannot_be_exported(photo_record):
    doc = read(photo_record)
    doc['status'] = 'running'
    photo_record.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(ValueError):
        export_photo_candidates(photo_record, photo_record.parent / 'out.json')


def test_size_limit_does_not_publish_partial_file(photo_record, monkeypatch):
    import mypackage.candidate_export as exporter
    monkeypatch.setattr(exporter, 'MAX_EXPORT_BYTES', 10)
    destination = photo_record.parent / 'export.json'
    with pytest.raises(ValueError):
        export_photo_candidates(photo_record, destination)
    assert not destination.exists()


def test_existing_run_identity_is_used_and_failed_photos_not_exported(photo_record):
    from uuid import uuid4
    doc = read(photo_record)
    doc['run_id'] = str(uuid4())
    doc['photos'][1]['status'] = 'failed'
    photo_record.write_text(json.dumps(doc), encoding='utf-8')
    destination = photo_record.parent / 'out.json'
    export_photo_candidates(photo_record, destination)
    payload = read(destination)
    assert payload['run']['id'] == doc['run_id']
    assert len(payload['candidates']) == 1 and payload['run']['failedCount'] == 1


def test_reopened_dialog_exports_latest_saved_review(photo_record, qt_application, monkeypatch):
    from mypackage.candidate_review import CandidateReviewDialog
    from mypackage import candidate_export_ui as ui
    destination = photo_record.parent / 'out.json'
    monkeypatch.setattr(ui.QFileDialog, 'getSaveFileName', lambda *args: (str(destination), ''))
    messages = []
    monkeypatch.setattr(ui.QMessageBox, 'information', lambda *args: messages.append(args[-1]))
    dialog = CandidateReviewDialog(photo_record)
    dialog.set_review('hold')
    dialog.export_button.click()
    assert read(destination)['candidates'][0]['review'] == 'hold'
    assert '후보 2건' in messages[0]
    dialog.close()


def test_export_progress_stays_responsive_and_cannot_close_mid_write(photo_record, qt_application,
                                                                  monkeypatch):
    import threading
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget
    from mypackage import candidate_export_ui as ui
    destination = photo_record.parent / 'out.json'
    monkeypatch.setattr(ui.QFileDialog, 'getSaveFileName', lambda *args: (str(destination), ''))
    monkeypatch.setattr(ui.QMessageBox, 'information', lambda *args: None)
    original = ui.export_photo_candidates
    released = threading.Event()
    ticks = []

    def slow(*args):
        assert released.wait(3)
        return original(*args)

    def tick():
        for widget in qt_application.topLevelWidgets():
            if isinstance(widget, ui.CandidateExportProgress) and widget.isVisible():
                widget.reject()
                ticks.append(widget.isVisible())
        released.set()

    monkeypatch.setattr(ui, 'export_photo_candidates', slow)
    QTimer.singleShot(50, tick)
    parent = QWidget()
    try:
        assert ui.choose_photo_export(parent, photo_record) == str(destination)
        assert ticks == [True] and destination.exists()
    finally:
        released.set()
        parent.close()


@pytest.mark.parametrize('field,value', [('captured_at', '2026-10-18'),
                                         ('captured_at', '2026-02-31T12:00:00'),
                                         ('image_size', [200.5, 120])])
def test_invalid_portable_metadata_is_rejected_before_publication(photo_record, field, value):
    document = read(photo_record)
    document['photos'][0][field] = value
    photo_record.write_text(json.dumps(document), encoding='utf-8')
    destination = photo_record.parent / 'export.json'
    with pytest.raises(ValueError):
        export_photo_candidates(photo_record, destination)
    assert not destination.exists()


def test_legacy_missing_preview_keeps_candidate_and_status(photo_record):
    (photo_record.parent / 'thumb.jpg').unlink()
    destination = photo_record.parent / 'out.json'
    export_photo_candidates(photo_record, destination)
    assert len(read(destination)['candidates']) == 2
    assert all(c['thumbnail'] is None for c in read(destination)['candidates'])
