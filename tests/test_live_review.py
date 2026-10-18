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
