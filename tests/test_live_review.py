from PySide6.QtWidgets import QApplication

from mypackage.live_events import LiveEventRecorder, load_live_events, write_live_records
from mypackage.live_review import LiveRecordsWidget


def test_finished_event_review_note_copy_and_report(tmp_path, qt_application):
    recorder = LiveEventRecorder(confirmation_frames=1)
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    recorder.close('disconnected')
    path, _ = write_live_records(tmp_path, recorder.document('26.1014', 'disconnected'))
    widget = LiveRecordsWidget(path)
    widget.table.selectRow(0)
    widget.note_edit.setText('C3 쪽')
    widget.save_note_button.click()
    widget.review_buttons[2].click()
    event = load_live_events(path)['events'][0]
    assert event['note'] == 'C3 쪽' and event['review'] == 'hold'
    widget.copy_button.click()
    assert '14:32' in QApplication.clipboard().text()
    assert 'C3 쪽' in QApplication.clipboard().text()
    assert (tmp_path / 'search_report.html').is_file()
    widget.close()


def test_active_note_uses_worker_command_and_requires_save_acknowledgement(qt_application):
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    widget = LiveRecordsWidget()
    edits = []
    widget.edit_requested.connect(lambda event_id, changes: edits.append((event_id, changes)))
    widget.apply_event({'event': recorder.events[0], 'saved': True})
    widget.table.selectRow(0)
    widget.note_edit.setText('C4 방향')
    widget.save_note_button.click()
    assert edits == [('live-000001', {'note': 'C4 방향'})]
    assert '요청' in widget.save_status.text()
    recorder.update(*edits[0])
    widget.apply_event({'event': recorder.events[0], 'saved': True})
    assert '저장됨' in widget.save_status.text()
    widget.close()


def test_space_saves_scene_without_intercepting_spaces_in_notes(qt_application):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from mypackage import gui
    window = gui.PreviewWindow()
    window.configure_source(gui.CAPTURE_BOARD_SOURCE)
    requests = []
    window.snapshot_requested.connect(lambda: requests.append(True))
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    window.live_records.apply_event({'event': recorder.events[0], 'saved': True})
    window.show()
    window.activateWindow()
    qt_application.processEvents()
    window.preview_label.setFocus()
    QTest.keyClick(window, Qt.Key.Key_Space)
    assert requests == [True]
    window.tabs.setCurrentIndex(1)
    window.live_records.note_edit.setFocus()
    QTest.keyClicks(window.live_records.note_edit, 'C3 side')
    assert window.live_records.note_edit.text() == 'C3 side'
    assert requests == [True]
    window._closing_programmatically = True
    window.close()


def test_running_checkpoint_is_read_only_when_reopened(tmp_path, qt_application):
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    path, _ = write_live_records(tmp_path, recorder.document('26.1014', 'running'))
    widget = LiveRecordsWidget(path)
    widget.table.selectRow(0)
    assert not widget.save_note_button.isEnabled()
    widget.commit({'note': 'must not change'})
    assert load_live_events(path)['events'][0]['note'] == ''
    widget.close()


def test_incoming_event_does_not_replace_unsaved_note_text(qt_application):
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    widget = LiveRecordsWidget()
    widget.apply_event({'event': recorder.events[0], 'saved': True})
    widget.note_edit.setText('operator is typing')
    recorder.observe(.5, '2026-10-18T14:32:00.500+09:00', [.9])
    widget.apply_event({'event': recorder.events[0], 'saved': False})
    assert widget.note_edit.text() == 'operator is typing'
    widget.close()


def test_finish_reconciles_all_unacknowledged_edits_and_preserves_newer_draft(tmp_path, qt_application):
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    recorder.close('gap')
    recorder.observe(3, '2026-10-18T14:32:03+09:00', [.9])
    widget = LiveRecordsWidget()
    for event in recorder.events:
        widget.apply_event({'event': event, 'saved': True})
    widget.table.selectRow(0)
    widget.note_edit.setText('first note')
    widget.save_note()
    widget.commit({'review': 'hold'})
    widget.table.selectRow(1)
    widget.note_edit.setText('saved request')
    widget.save_note()
    widget.note_edit.setText('newer unsaved draft')
    recorder.close('disconnected')
    path, _ = write_live_records(tmp_path, recorder.document('26.1018', 'disconnected'))
    widget.set_finished(path)
    events = load_live_events(path)['events']
    assert events[0]['note'] == 'first note' and events[0]['review'] == 'hold'
    assert events[1]['note'] == 'saved request'
    assert widget._pending == {}
    assert widget.note_edit.text() == 'newer unsaved draft'
    assert '미저장' in widget.save_status.text()
    widget.save_note()
    assert load_live_events(path)['events'][1]['note'] == 'newer unsaved draft'
    assert 'first note' in (tmp_path / 'search_report.html').read_text()
    widget.close()


def test_finish_keeps_failed_pending_edit_visible_and_retryable(tmp_path, qt_application, monkeypatch):
    import mypackage.live_review as review
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    widget = LiveRecordsWidget()
    widget.apply_event({'event': recorder.events[0], 'saved': True})
    widget.note_edit.setText('retry this note')
    widget.save_note()
    widget.commit({'review': 'hold'})
    recorder.close('cancelled')
    path, _ = write_live_records(tmp_path, recorder.document('26.1018', 'cancelled'))
    original_save = review.save_live_review
    monkeypatch.setattr(review, 'save_live_review', lambda *args: (_ for _ in ()).throw(
        OSError('disk full')))
    widget.set_finished(path)
    assert widget._pending == {'live-000001': {'note': 'retry this note', 'review': 'hold'}}
    assert widget.note_edit.text() == 'retry this note'
    assert 'disk full' in widget.save_status.text()
    assert load_live_events(path)['events'][0]['note'] == ''
    monkeypatch.setattr(review, 'save_live_review', original_save)
    widget.save_note()
    saved = load_live_events(path)['events'][0]
    assert saved['note'] == 'retry this note' and saved['review'] == 'hold'
    assert widget._pending == {}
    widget.close()


def test_finish_acknowledges_json_but_reports_derived_csv_failure(tmp_path, qt_application,
                                                               monkeypatch):
    import mypackage.live_events as live
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-18T14:32:00+09:00', [.9])
    widget = LiveRecordsWidget()
    widget.apply_event({'event': recorder.events[0], 'saved': True})
    widget.note_edit.setText('JSON survives CSV failure')
    widget.save_note()
    recorder.close('failed')
    path, _ = write_live_records(tmp_path, recorder.document('26.1018', 'failed'))

    def fail_csv(*args):
        raise OSError('CSV locked')

    monkeypatch.setattr(live, 'write_bytes_file', fail_csv)
    widget.set_finished(path)
    assert load_live_events(path)['events'][0]['note'] == 'JSON survives CSV failure'
    assert widget._pending == {}
    assert widget.note_edit.text() == 'JSON survives CSV failure'
    assert 'CSV locked' in widget.save_status.text()
    assert 'JSON survives CSV failure' in (tmp_path / 'search_report.html').read_text()
    widget.close()
