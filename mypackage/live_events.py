"""Time-window events from capture-board inference, independent of preview refresh."""

import copy
import csv
import io
import math
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLockFile

from mypackage.detection_records import (
    REVIEW_LABELS, _finite_number, _validate_id, asset_path, read_record_json,
)
from mypackage.run_report import write_bytes_file, write_json_file


class LiveEventRecorder:
    def __init__(self, gap_seconds=2, confirmation_frames=3, alert_confidence=.5, cooldown_seconds=5):
        if not (_finite_number(gap_seconds, 0, 30)
                and isinstance(confirmation_frames, int) and 1 <= confirmation_frames <= 60
                and _finite_number(alert_confidence, 0, 1)
                and _finite_number(cooldown_seconds, .1, 120)):
            raise ValueError("실시간 알림·기록 설정을 확인해 주세요.")
        self.settings = dict(gap_seconds=gap_seconds, confirmation_frames=confirmation_frames,
                             alert_confidence=alert_confidence, cooldown_seconds=cooldown_seconds)
        self.events = []
        self.current = None
        self._started = 0
        self._last_seen = 0
        self._consecutive = 0
        self._last_alert = -math.inf

    def _new_event(self, captured_at, kind):
        event = {
            "id": f"live-{len(self.events) + 1:06d}", "kind": kind,
            "started_at": captured_at, "ended_at": captured_at, "duration_seconds": 0,
            "max_people": 0, "peak_confidence": 0, "note": "", "review": "unreviewed",
            "snapshots": [], "termination": "active" if kind == "detection" else "manual",
            "location_kind": "unknown", "gps": None, "crosscheck": None,
        }
        self.events.append(event)
        return event

    def observe(self, now, captured_at, confidences):
        if self.current is not None and now - self._last_seen > self.settings["gap_seconds"]:
            self.close("gap")
        confidences = [float(value) for value in confidences if _finite_number(value, 0, 1)]
        if not confidences:
            self._consecutive = 0
            return False
        if self.current is None:
            self.current = self._new_event(captured_at, "detection")
            self._started = now
        self._last_seen = now
        event = self.current
        event["ended_at"] = captured_at
        event["duration_seconds"] = max(0, now - self._started)
        event["max_people"] = max(event["max_people"], len(confidences))
        event["peak_confidence"] = max(event["peak_confidence"], max(confidences))
        self._consecutive = (self._consecutive + 1 if max(confidences) >= self.settings[
            "alert_confidence"] else 0)
        alert = (self._consecutive >= self.settings["confirmation_frames"]
                 and now - self._last_alert >= self.settings["cooldown_seconds"])
        if alert:
            self._last_alert = now
            self._consecutive = 0
        return alert

    def close(self, status):
        if self.current is not None:
            self.current["termination"] = status
            self.current = None
        self._consecutive = 0

    def manual_event(self, _now, captured_at):
        return self.current if self.current is not None else self._new_event(captured_at, "manual")

    def update(self, event_id, changes):
        if not changes or set(changes) - {"note", "review"}:
            raise ValueError("메모와 확인 상태만 수정할 수 있습니다.")
        if "note" in changes and (not isinstance(changes["note"], str) or len(changes["note"]) > 500):
            raise ValueError("메모는 500자 이내로 입력해 주세요.")
        if "review" in changes and changes["review"] not in REVIEW_LABELS:
            raise ValueError("이벤트 확인 상태를 확인해 주세요.")
        for event in self.events:
            if event["id"] == event_id:
                event.update(changes)
                return event
        raise ValueError("수정할 이벤트를 찾지 못했습니다.")

    def document(self, version, status):
        return {"schema_version": 1, "kind": "live_events", "app_version": version,
                "status": status, "count_mode": "time_window_events",
                "settings": dict(self.settings), "events": copy.deepcopy(self.events)}


def load_live_events(path):
    path = Path(path)
    document = read_record_json(path)
    if document.get("kind") != "live_events" or not isinstance(document.get("events"), list):
        raise ValueError("실시간 이벤트 기록이 아닙니다.")
    identities = set()
    for event in document["events"]:
        if not isinstance(event, dict):
            raise ValueError("잘못된 이벤트 기록입니다.")
        _validate_id(event.get("id"), identities)
        if event.get("kind") not in {"detection", "manual"}:
            raise ValueError("잘못된 이벤트 종류입니다.")
        if (type(event.get("max_people")) is not int
                or not _finite_number(event.get("max_people"), 0, 100000)
                or not _finite_number(event.get("peak_confidence"), 0, 1)
                or not _finite_number(event.get("duration_seconds"), 0, 7 * 86400)
                or event.get("review") not in REVIEW_LABELS
                or not isinstance(event.get("note"), str) or len(event["note"]) > 500
                or not isinstance(event.get("snapshots"), list)):
            raise ValueError("이벤트 집계·메모·확인 상태를 확인해 주세요.")
        for key in ("started_at", "ended_at"):
            try:
                instant = datetime.fromisoformat(event[key])
                if instant.tzinfo is None:
                    raise ValueError("시간대 없음")
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("이벤트 시각·시간대가 유효하지 않습니다.") from error
        for snapshot in event["snapshots"]:
            if not isinstance(snapshot, dict) or not snapshot.get("file"):
                raise ValueError("잘못된 장면 파일 기록입니다.")
            asset_path(path.parent, snapshot["file"])
    return document


def _csv_safe(value):
    value = str(value if value is not None else "")
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")):
        return "'" + value
    return value


def write_live_records(folder, document):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = folder / "live_events.json", folder / "live_events.csv"
    write_json_file(json_path, document)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["번호", "시작 시각", "종료 시각", "지속(초)", "최고 신뢰도", "최대 동시 인원",
                     "메모", "장면 파일", "사람 확인", "매칭 사진", "위도", "경도", "격자 칸", "크로스체크"])
    for event in document["events"]:
        writer.writerow([_csv_safe(value) for value in (
            event["id"], event["started_at"], event["ended_at"],
            round(event["duration_seconds"], 3), event["peak_confidence"], event["max_people"],
            event["note"], "; ".join(s["file"] for s in event["snapshots"]),
            REVIEW_LABELS[event["review"]], "", "", "", "", "대응 미확인",
        )])
    write_bytes_file(csv_path, buffer.getvalue().encode("utf-8-sig"))
    return json_path, csv_path


def save_live_review(path, event_id, changes):
    path = Path(path)
    lock = QLockFile(str(path) + ".edit.lock")
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise OSError("다른 창이 기록을 수정 중입니다. 잠시 후 다시 시도해 주세요.")
    try:
        document = load_live_events(path)
        recorder = LiveEventRecorder()
        recorder.events = document["events"]
        recorder.update(event_id, changes)
        write_live_records(path.parent, document)
        return document
    finally:
        lock.unlock()


def event_report_message(event):
    instant = datetime.fromisoformat(event["started_at"]).strftime("%H:%M:%S")
    description = (f"사람 후보 최대 동시 {event['max_people']}명" if event["kind"] == "detection"
                   else "수동 저장 장면(사람 탐지 확인 안 됨)")
    note = f" · 메모: {event['note']}" if event["note"] else ""
    return (f"{instant} {description} · {event['duration_seconds']:.1f}초 · "
            f"{REVIEW_LABELS[event['review']]}{note} · 위치 미확인")
