import copy
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QPushButton

from mypackage import gui
from mypackage.live_events import LiveEventRecorder, load_live_events
from mypackage.live_review import LiveRecordsWidget


def events():
    recorder = LiveEventRecorder()
    recorder.observe(0, '2026-10-27T14:00:00+09:00', [.9])
    recorder.close('gap')
    recorder.observe(3, '2026-10-27T14:00:03+09:00', [.9])
    return recorder.events


def test_unsaved_notes_survive_switching_rows_and_event_refresh(qt_application):
    widget = LiveRecordsWidget()
    for event in events():
        widget.apply_event({'event': event, 'saved': True})
    widget.table.selectRow(0)
    widget.note_edit.setText('첫 구간 작성 중')
    widget.table.selectRow(1)
    widget.note_edit.setText('둘째 구간 작성 중')
    widget.apply_event({'event': events()[0], 'saved': False})
    widget.table.selectRow(0)
    assert widget.note_edit.text() == '첫 구간 작성 중'
    widget.table.selectRow(1)
    assert widget.note_edit.text() == '둘째 구간 작성 중'
    assert all(event['note'] == '' for event in widget.events.values())
    widget.close()


def test_save_failure_and_alert_remain_visible_after_preview_updates(qt_application, monkeypatch):
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    preview = window.ensure_preview_window()
    preview.configure_source(gui.CAPTURE_BOARD_SOURCE)
    preview.show()
    beeps = []
    monkeypatch.setattr(gui.QApplication, 'beep', lambda: beeps.append(True))
    preview.mute_button.setChecked(True)
    event = copy.deepcopy(events()[0])
    window.handle_live_alert(event)
    assert not beeps
    window.handle_live_scene({'trigger': 'manual', 'saved': False, 'count': 0})
    window.handle_live_warning('수동 장면 저장 실패: 시험용 디스크 오류')
    window.handle_live_event({'event': event, 'saved': True})
    window._start_preview_updates()
    window.update_preview_frame(QImage(32, 24, QImage.Format.Format_RGB888))
    window._display_pending_preview_frame()
    preview.tabs.setCurrentIndex(1)
    qt_application.processEvents()
    assert '최근 알림' in preview.alert_status.text() and preview.alert_status.isVisible()
    assert '디스크 오류' in preview.storage_warning.text() and preview.storage_warning.isVisible()
    assert '수동 저장 실패' in preview.scene_status.text()
    assert not preview._snapshot_shortcut.autoRepeat()
    preview.configure_source(gui.CAPTURE_BOARD_SOURCE)
    assert preview.storage_warning.isHidden() and not preview.storage_warning.text()
    preview.close_preview_window()
    window._closing_without_confirmation = True
    window.close()


def test_saved_ack_does_not_claim_a_newer_note_draft_was_saved(qt_application):
    widget = LiveRecordsWidget()
    event = events()[0]
    widget.apply_event({'event': event, 'saved': True})
    widget.note_edit.setText('저장 요청한 메모')
    widget.save_note()
    widget.note_edit.setText('뒤이어 작성한 새 초안')
    event['note'] = '저장 요청한 메모'
    widget.apply_event({'event': event, 'saved': True})
    assert widget.note_edit.text() == '뒤이어 작성한 새 초안'
    assert '미저장' in widget.save_status.text()
    assert widget.events[event['id']]['note'] == '저장 요청한 메모'
    widget.close()


def test_snapshot_waits_for_a_frame_received_after_request(tmp_path, qt_application, monkeypatch):
    worker = gui.DetectionWorker({'source': gui.CAPTURE_BOARD_SOURCE})
    monkeypatch.setattr(gui.time, 'monotonic', lambda: 20.0)
    outcomes = []
    worker.live_scene_signal.connect(outcomes.append)
    worker.request_snapshot()
    worker._process_live_frame(tmp_path, np.zeros((16, 16, 3), np.uint8), [],
                               received_at=10, captured_at='2026-10-27T14:00:10+09:00')
    assert not worker.snapshot_files and not outcomes
    worker._process_live_frame(tmp_path, np.full((16, 16, 3), 220, np.uint8), [],
                               received_at=21, captured_at='2026-10-27T14:00:21+09:00')
    assert len(worker.snapshot_files) == 1
    assert cv2.imread(worker.snapshot_files[0]).mean() > 210
    event = load_live_events(tmp_path / 'live_events.json')['events'][0]
    assert event['snapshots'][0]['captured_at'] == '2026-10-27T14:00:21+09:00'
    assert event['max_people'] == 0 and outcomes == [{'trigger': 'manual', 'saved': True, 'count': 1}]
    worker._take_live_commands(seal=True)
    assert worker.request_snapshot() is False


def test_auto_scene_failure_keeps_alert_and_event_record(tmp_path, qt_application, monkeypatch):
    worker = gui.DetectionWorker({'source': gui.CAPTURE_BOARD_SOURCE,
                                  'live_settings': {'confirmation_frames': 1}})
    alerts, scenes = [], []
    worker.live_alert_signal.connect(alerts.append)
    worker.live_scene_signal.connect(scenes.append)
    monkeypatch.setattr(gui.cv2, 'imencode', lambda *args: (False, None))
    worker._process_live_frame(tmp_path, np.zeros((16, 16, 3), np.uint8), [.9])
    assert len(alerts) == 1 and scenes == [{'trigger': 'auto', 'saved': False, 'count': 0}]
    assert not worker.snapshot_files
    assert load_live_events(tmp_path / 'live_events.json')['events'][0]['max_people'] == 1
    assert any('자동 장면 저장 실패' in warning for warning in worker.warnings)


def test_live_settings_explain_effective_threshold_and_vehicle_only(qt_application):
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    window.comboBox_source.setCurrentText(gui.CAPTURE_BOARD_SOURCE)
    window.comboBox_percentage.setCurrentText('80%')
    assert '실제 신뢰도 기준 80%' in window.live_settings.note.text()
    assert '음소거는 소리만' in window.live_settings.note.text()
    window.radioButton_car.setChecked(True)
    assert '차량만 선택됨' in window.live_settings.note.text()
    assert not window.live_settings.fields['confirmation_frames'].isEnabled()
    assert window.live_settings.values()['confirmation_frames'] == 3
    window.radioButton_person.setChecked(True)
    assert window.live_settings.fields['confirmation_frames'].isEnabled()
    window._closing_without_confirmation = True
    window.close()


def test_dashboard_section_controls_are_reachable_in_small_window(tmp_path, qt_application):
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    window.show()
    window.resize(560, 560)
    window.remember_detection_result({'detections_path': str(tmp_path / 'detections.json')}, '검증')
    qt_application.processEvents()
    window.scrollArea.ensureWidgetVisible(window.dashboard_link_group)
    qt_application.processEvents()
    for button in (window.export_candidates_button, window.candidate_folder_button):
        assert button.visibleRegion().boundingRect() == button.rect()
    assert window.scrollAreaWidgetContents.width() <= window.scrollArea.viewport().width()
    window._closing_without_confirmation = True
    window.close()


def test_unified_result_button_preserves_video_and_missing_original(tmp_path, qt_application,
                                                                  monkeypatch):
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    assert not any(button.text() == '원본과 비교' for button in window.resultCard.findChildren(QPushButton))
    assert window.export_candidates_button.parentWidget() is window.dashboard_link_group
    assert window.candidate_folder_status.parentWidget() is window.dashboard_link_group
    detected = tmp_path / 'detected.png'
    Image.new('RGB', (80, 60), 'green').save(detected)
    window.remember_detection_result({'output_files': [str(detected)],
                                      'original_files': [str(tmp_path / 'missing.jpg')]}, '검증')
    window.open_result_button.click()
    assert window._comparison_dialog.isVisible() and not window._comparison_dialog.comparison_mode
    window._comparison_dialog.close()
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, 'openUrl', lambda url: opened.append(url) or True)
    video = tmp_path / 'detected.mp4'
    video.write_bytes(b'video-fixture')
    window.remember_detection_result({'output_files': [str(video)]}, '검증')
    assert window.open_result_button.text() == '영상 결과보기'
    window.open_result_button.click()
    assert Path(opened[0].toLocalFile()) == video
    window._closing_without_confirmation = True
    window.close()
