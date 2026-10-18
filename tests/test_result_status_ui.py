import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mypackage import gui


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def window(qapp):
    main_window = gui.Ui_MainWindow()
    yield main_window

    main_window.worker = None
    main_window.close_progress_dialog()
    main_window._closing_without_confirmation = True
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


def _base_result(**overrides):
    result = {
        "source": "사진",
        "image_count": 3,
        "detected_files": ["good.jpg"],
        "original_files": [],
        "output_files": [],
        "output_folder": "/tmp/detected",
        "folder_status": "결과 폴더 준비됨",
        "execution_time": 1.25,
        "total_people": 1,
        "total_cars": 0,
        "processed_count": 3,
        "attempted_count": 3,
        "succeeded_count": 2,
        "failed_count": 1,
        "errors": ["bad.jpg 처리 실패"],
        "status": gui.DETECTION_STATUS_PARTIAL,
        "only_person": False,
        "only_car": False,
    }
    result.update(overrides)
    return result


def test_partial_photo_summary_uses_warning_and_separate_counts(window, monkeypatch):
    messages = []
    monkeypatch.setattr(
        gui.QMessageBox,
        "warning",
        lambda _parent, title, message: messages.append((title, message)),
    )

    window.display_results_new(_base_result())

    assert len(messages) == 1
    title, message = messages[0]
    assert title == "AI 객체 탐지 부분 완료"
    assert "처리 시도: 3장" in message
    assert "처리 성공: 2장" in message
    assert "처리 실패: 1장" in message
    assert "- bad.jpg 처리 실패" in message


def test_failed_result_is_not_presented_as_completed(window, monkeypatch):
    critical_messages = []
    information_messages = []
    monkeypatch.setattr(
        gui.QMessageBox,
        "critical",
        lambda _parent, title, message: critical_messages.append((title, message)),
    )
    monkeypatch.setattr(
        gui.QMessageBox,
        "information",
        lambda _parent, title, message: information_messages.append((title, message)),
    )

    window.display_results_new(
        _base_result(
            detected_files=[],
            succeeded_count=0,
            failed_count=3,
            status=gui.DETECTION_STATUS_FAILED,
        )
    )

    assert len(critical_messages) == 1
    assert critical_messages[0][0] == "AI 객체 탐지 실패"
    assert "처리 성공: 0장" in critical_messages[0][1]
    assert "처리 실패: 3장" in critical_messages[0][1]
    assert "성공적으로 분석된 사진이 없습니다" in critical_messages[0][1]
    assert "탐지된 사람 또는 차량이 없습니다" not in critical_messages[0][1]
    assert information_messages == []


def test_capture_disconnect_summary_reports_frames_and_warning(window, monkeypatch):
    messages = []
    monkeypatch.setattr(
        gui.QMessageBox,
        "warning",
        lambda _parent, title, message: messages.append((title, message)),
    )

    window.display_results_new(
        _base_result(
            source=gui.CAPTURE_BOARD_SOURCE,
            image_count=0,
            detected_files=[],
            errors=["캡처보드 연결을 확인해 주세요."],
            status=gui.DETECTION_STATUS_DISCONNECTED,
            video_frame_count=42,
            reported_video_frame_count=None,
        )
    )

    assert len(messages) == 1
    title, message = messages[0]
    assert title == "외부 영상 입력 연결 끊김"
    assert "영상 탐지 상태: 입력 연결 끊김" in message
    assert "처리 프레임: 42개" in message


def test_cancelled_run_keeps_report_failure_visible_in_result_tab(window, monkeypatch):
    monkeypatch.setattr(gui.QMessageBox, "information", lambda *_args: None)
    warning = "실행 요약(run_summary.json)을 저장하지 못했습니다: 디스크 공간 부족"
    window.present_detection_result(
        _base_result(status=gui.DETECTION_STATUS_CANCELLED, report_warning=warning)
    )
    assert warning in window.result_summary.toPlainText()


def test_result_tab_exposes_saved_report_path(window, monkeypatch):
    monkeypatch.setattr(gui.QMessageBox, "warning", lambda *_args: None)
    report_path = "/tmp/results/run_summary.json"
    window.display_results_new(_base_result(report_path=report_path))
    assert f"실행 기록: {report_path}" in window.result_summary.toPlainText()


def test_native_thread_finish_prefers_structured_failure_result(window, monkeypatch):
    result = _base_result(
        detected_files=[],
        succeeded_count=0,
        failed_count=3,
        status=gui.DETECTION_STATUS_FAILED,
        fatal_error="model load failed",
    )
    presented = []
    fallback_errors = []
    window._pending_detection_error = "model load failed"
    window._pending_detection_result = result
    monkeypatch.setattr(window, "present_detection_result", presented.append)
    monkeypatch.setattr(
        gui.QMessageBox,
        "critical",
        lambda *_args: fallback_errors.append(True),
    )

    window.on_worker_thread_finished()

    assert presented == [result]
    assert fallback_errors == []
    assert window._pending_detection_error is None
    assert window._pending_detection_result is None


@pytest.mark.parametrize('record_name', ['detections.json', 'live_events.json'])
def test_invalid_record_does_not_destroy_existing_dialog_or_block_next_open(window, tmp_path,
                                                                         monkeypatch, qapp,
                                                                         record_name):
    from mypackage.live_events import LiveEventRecorder, write_live_records
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid
    valid, invalid = tmp_path / record_name, tmp_path / 'invalid.json'
    if record_name == 'live_events.json':
        write_live_records(tmp_path, LiveEventRecorder().document('26.1018', 'disconnected'))
    else:
        valid.write_text('{"schema_version": 1, "photos": []}')
    invalid.write_text('{bad json')
    warnings = []
    monkeypatch.setattr(gui.QMessageBox, 'warning', lambda *args: warnings.append(args[-1]))
    window.open_candidate_review(valid)
    previous = window._review_dialog
    window.open_candidate_review(invalid)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert isValid(previous)
    assert window._review_dialog is previous
    window.open_candidate_review(valid)
    qapp.processEvents()
    assert len(warnings) == 1
    assert window._review_dialog is not previous and isValid(window._review_dialog)
    window._review_dialog.close()
