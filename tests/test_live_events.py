import codecs

import pytest

from mypackage.live_events import LiveEventRecorder, load_live_events, write_live_records


def at(seconds):
    return f'2026-10-18T12:00:{seconds:06.3f}+09:00'


def test_events_use_gap_and_alert_threshold_without_changing_detection_candidates():
    recorder = LiveEventRecorder(confirmation_frames=2, alert_confidence=.5, cooldown_seconds=5)
    assert not recorder.observe(0, at(0), [.2])
    assert len(recorder.events) == 1
    assert not recorder.observe(.1, at(.1), [.7])
    assert recorder.observe(.2, at(.2), [.8, .6])
    assert not recorder.observe(.3, at(.3), [.9])
    recorder.observe(1, at(1), [])
    recorder.observe(2, at(2), [.7])
    assert len(recorder.events) == 1
    recorder.observe(4.1, at(4.1), [])
    recorder.observe(5, at(5), [.8])
    assert len(recorder.events) == 2
    assert recorder.events[0]['max_people'] == 2
    assert recorder.events[0]['ended_at'] == at(2)
    assert recorder.events[0]['termination'] == 'gap'
    recorder.close('disconnected')
    assert recorder.events[1]['termination'] == 'disconnected'


def test_slow_continuous_positive_frames_still_confirm_alerts():
    recorder = LiveEventRecorder()
    alerts = [recorder.observe(second, at(second), [.95]) for second in (0, 3, 6, 9)]
    assert alerts == [False, False, True, False]
    assert len(recorder.events) == 1
    assert recorder.events[0]['duration_seconds'] == 9


def test_explicit_negative_gap_resets_confirmation_even_with_slow_frames():
    recorder = LiveEventRecorder(confirmation_frames=2)
    recorder.observe(0, at(0), [.95])
    recorder.observe(3, at(3), [])
    assert not recorder.observe(6, at(6), [.95])
    assert recorder.observe(9, at(9), [.95])
    assert len(recorder.events) == 2


def test_close_keeps_events_and_csv_is_utf8_bom_and_neutralizes_formulas(tmp_path):
    recorder = LiveEventRecorder(confirmation_frames=1)
    recorder.observe(0, at(0), [.9])
    recorder.update(recorder.events[0]['id'], {'note': '=HYPERLINK("bad")', 'review': 'hold'})
    recorder.close('cancelled')
    json_path, csv_path = write_live_records(tmp_path, recorder.document('26.1014', 'cancelled'))
    document = load_live_events(json_path)
    assert document['status'] == 'cancelled'
    assert document['events'][0]['note'].startswith('=HYPERLINK')
    assert csv_path.read_bytes().startswith(codecs.BOM_UTF8)
    assert "'=HYPERLINK" in csv_path.read_text(encoding='utf-8-sig')
    assert document['events'][0]['review'] == 'hold'


def test_manual_scene_without_detection_does_not_claim_a_person():
    recorder = LiveEventRecorder()
    event = recorder.manual_event(0, at(0))
    assert event['kind'] == 'manual'
    assert event['max_people'] == 0
    assert event['review'] == 'unreviewed'
    assert recorder.current is None
    with pytest.raises(ValueError):
        recorder.update(event['id'], {'max_people': 1})
