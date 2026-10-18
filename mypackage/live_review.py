"""Native capture-board settings and event review, shared by live and reopened records."""

import copy
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from mypackage.detection_records import REVIEW_LABELS, asset_path
from mypackage.live_events import event_report_message, load_live_events, save_live_review
from mypackage.search_report import create_search_report


class DeliberateNumber(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class LiveSettingsWidget(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("실시간 알림·기록", parent)
        grid = QGridLayout(self)
        self.fields = {}
        definitions = [
            ("alert_confidence", "알림 신뢰도(%)", 0, 100, 50, 0),
            ("confirmation_frames", "알림 연속 프레임", 1, 60, 3, 0),
            ("cooldown_seconds", "알림 반복 간격(초)", .1, 120, 5, 1),
            ("gap_seconds", "구간 연결 간격(초)", 0, 30, 2, 1),
        ]
        for index, (key, title, low, high, value, decimals) in enumerate(definitions):
            label, field = QLabel(title), DeliberateNumber()
            field.setRange(low, high)
            field.setDecimals(decimals)
            field.setValue(value)
            field.setAccessibleName(title)
            label.setBuddy(field)
            grid.addWidget(label, index // 2, (index % 2) * 2)
            grid.addWidget(field, index // 2, (index % 2) * 2 + 1)
            self.fields[key] = field
        note = QLabel("탐지 기준은 유지합니다. 알림 장면은 자동 저장되며 미리보기에서 음소거·수동 저장이 가능합니다.")
        note.setWordWrap(True)
        grid.addWidget(note, 2, 0, 1, 4)

    def values(self):
        values = {key: field.value() for key, field in self.fields.items()}
        values["alert_confidence"] /= 100
        values["confirmation_frames"] = int(values["confirmation_frames"])
        return values


class LiveRecordsWidget(QWidget):
    edit_requested = Signal(str, dict)

    def __init__(self, record_path=None, parent=None):
        super().__init__(parent)
        self.record_path = None
        self.active = record_path is None
        self.read_only_running = False
        self.events = {}
        self._pending = {}
        layout = QVBoxLayout(self)
        notice = QLabel("시간 구간 기록이며 동일인 추적·고유 인원 집계가 아닙니다. 위치는 미확인입니다.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["번호", "시작", "마지막", "초", "최대 동시", "신뢰도", "확인", "메모"])
        self.table.setAccessibleName("실시간 탐지 구간 기록표")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        layout.addWidget(self.table, 1)
        notes = QHBoxLayout()
        self.note_edit = QLineEdit()
        self.note_edit.setMaxLength(500)
        self.note_edit.setPlaceholderText("선택 구간 메모 · 예: C3 쪽")
        self.note_edit.setAccessibleName("선택한 실시간 구간 메모")
        self.save_note_button = QPushButton("메모 저장")
        self.save_note_button.clicked.connect(self.save_note)
        self.note_edit.returnPressed.connect(self.save_note)
        notes.addWidget(self.note_edit, 1)
        notes.addWidget(self.save_note_button)
        layout.addLayout(notes)
        judgments = QHBoxLayout()
        self.review_buttons = []
        for state in ("person", "false_positive", "hold"):
            button = QPushButton(REVIEW_LABELS[state])
            button.setAccessibleName(f"선택 구간 {REVIEW_LABELS[state]}로 저장")
            button.clicked.connect(lambda _checked=False, review=state: self.commit({"review": review}))
            judgments.addWidget(button)
            self.review_buttons.append(button)
        layout.addLayout(judgments)
        actions = QHBoxLayout()
        self.copy_button = QPushButton("보고 문구 복사")
        self.scene_button = QPushButton("장면 열기")
        self.report_button = QPushButton("보고서 만들고 열기")
        self.copy_button.clicked.connect(self.copy_message)
        self.scene_button.clicked.connect(self.open_scene)
        self.report_button.clicked.connect(self.open_report)
        for button in (self.copy_button, self.scene_button, self.report_button, self.save_note_button):
            button.setAccessibleName(button.text())
            button.setMinimumHeight(32)
            button.setAutoDefault(False)
        for button in (self.copy_button, self.scene_button, self.report_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.save_status = QLabel("구간을 선택해 메모·판정을 기록하세요.")
        self.save_status.setTextFormat(Qt.TextFormat.PlainText)
        self.save_status.setWordWrap(True)
        layout.addWidget(self.save_status)
        if record_path is not None:
            self.set_finished(record_path)
        self.selection_changed()

    def reset(self):
        self.active = True
        self.read_only_running = False
        self.events.clear()
        self._pending.clear()
        self.record_path = None
        self.table.setRowCount(0)
        self.note_edit.clear()
        self.selection_changed()
        self.save_status.setText("실시간 구간이 기록되면 선택해 메모·판정을 입력하세요.")

    def selected_event(self):
        item = self.table.item(self.table.currentRow(), 0)
        return self.events.get(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def selection_changed(self):
        event = self.selected_event()
        for control in [self.note_edit, self.save_note_button, self.copy_button, *self.review_buttons]:
            control.setEnabled(event is not None and not self.read_only_running)
        self.note_edit.setText(self._pending.get(event["id"], {}).get("note", event["note"])
                               if event else "")
        self.scene_button.setEnabled(bool(event and event["snapshots"] and self.record_path))
        self.report_button.setEnabled(not self.active and self.record_path is not None)

    def apply_event(self, payload):
        selected_before = self.selected_event()
        selected_id = selected_before["id"] if selected_before else None
        event = copy.deepcopy(payload["event"])
        event_id = event["id"]
        existed = event_id in self.events
        self.events[event_id] = event
        if payload.get("record_path"):
            self.record_path = Path(payload["record_path"])
        row = list(self.events).index(event_id)
        blocked = self.table.blockSignals(True)
        if not existed:
            self.table.insertRow(row)
        values = [event_id, datetime.fromisoformat(event["started_at"]).strftime("%H:%M:%S"),
                  datetime.fromisoformat(event["ended_at"]).strftime("%H:%M:%S"),
                  f"{event['duration_seconds']:.1f}", str(event["max_people"]),
                  f"{event['peak_confidence']:.0%}", REVIEW_LABELS[event["review"]], event["note"]]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, event_id)
            self.table.setItem(row, column, item)
        if selected_id in self.events:
            self.table.selectRow(list(self.events).index(selected_id))
        else:
            self.table.selectRow(row)
        self.table.blockSignals(blocked)
        if selected_id is None:
            self.selection_changed()
        pending = self._pending.get(event_id)
        if payload.get("saved") and pending and all(event.get(key) == value for key, value in pending.items()):
            self._pending.pop(event_id, None)
            self.save_status.setText(f"저장됨 · {event_id}")
        selected = self.selected_event()
        self.scene_button.setEnabled(bool(selected and selected["snapshots"] and self.record_path))

    def set_finished(self, record_path):
        path = Path(record_path)
        document = load_live_events(path)
        selected = self.selected_event()
        draft = self.note_edit.text()
        expected_note = (self._pending.get(selected["id"], {}).get("note", selected["note"])
                         if selected else "")
        has_draft = selected is not None and draft != expected_note
        self.active = False
        self.read_only_running = document.get("status") == "running"
        self.record_path = path
        errors = []
        had_pending = bool(self._pending)
        # The worker has stopped writing before emitting its final result. Replay
        # requests without an acknowledgement against that final file; an edit
        # arriving after the worker sealed its queue must not be silently lost.
        if not self.read_only_running:
            for event_id, changes in list(self._pending.items()):
                try:
                    save_live_review(path, event_id, changes)
                except Exception as error:
                    errors.append(str(error))
            document = load_live_events(path)
        for event in document["events"]:
            self.apply_event({"event": event, "saved": True})
        if had_pending and not self.read_only_running:
            try:
                create_search_report(path)
            except Exception as error:
                errors.append(f"보고서 갱신 실패: {error}")
        self.report_button.setEnabled(True)
        self.save_status.setText(
            "중간 저장 기록입니다. 종료 상태가 확정되기 전에는 편집할 수 없습니다."
            if self.read_only_running else "종료된 기록입니다. 메모·판정 변경은 파일에 저장합니다."
        )
        self.selection_changed()
        if has_draft:
            self.note_edit.setText(draft)
            self.save_status.setText("종료됨 · 미저장 메모를 유지했습니다. 메모 저장을 눌러 저장하세요.")
        elif had_pending and not self._pending and not errors:
            self.save_status.setText("종료됨 · 종료 직전 메모·판정까지 파일에 저장했습니다.")
        if errors or self._pending:
            detail = "; ".join(errors) or "저장 확인을 받지 못한 요청이 있습니다."
            self.save_status.setText(f"종료됨 · 기록/CSV 저장 확인 필요: {detail} · 다시 저장해 주세요.")

    def save_note(self):
        self.commit({"note": self.note_edit.text()})

    def commit(self, changes):
        if self.read_only_running:
            return
        event = self.selected_event()
        if event is None:
            return
        event_id = event["id"]
        if self.active:
            self._pending.setdefault(event_id, {}).update(changes)
            self.edit_requested.emit(event_id, changes)
            self.save_status.setText(f"저장 요청됨 · {event_id} · 워커 확인을 기다리는 중")
            return
        self._pending.setdefault(event_id, {}).update(changes)
        try:
            document = save_live_review(self.record_path, event_id, self._pending[event_id])
            for updated in document["events"]:
                self.apply_event({"event": updated, "saved": True})
            self.save_status.setText(f"저장됨 · {event_id}")
        except Exception as error:
            # JSON may have been committed even if the derived CSV could not be updated.
            try:
                for updated in load_live_events(self.record_path)["events"]:
                    self.apply_event({"event": updated, "saved": True})
            except Exception:
                pass
            self.save_status.setText(f"기록/CSV 저장 확인 필요: {error}")
            return
        try:
            create_search_report(self.record_path)
        except Exception as error:
            self.save_status.setText(f"기록은 저장됨 · 보고서 갱신 실패: {error}")

    def copy_message(self):
        event = self.selected_event()
        if event is not None:
            QApplication.clipboard().setText(event_report_message(event))

    def open_scene(self):
        event = self.selected_event()
        if event and event["snapshots"] and self.record_path:
            path = asset_path(self.record_path.parent, event["snapshots"][-1]["file"])
            if not path.is_file() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                self.save_status.setText("장면 파일을 열지 못했습니다. 저장 폴더를 확인하세요.")

    def open_report(self):
        if self.active or not self.record_path:
            return
        try:
            path = create_search_report(self.record_path)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
                raise OSError("브라우저를 열지 못했습니다. 저장 폴더에서 보고서를 확인하세요.")
        except Exception as error:
            self.save_status.setText(f"보고서 생성·열기 실패: {error}")


class LiveRecordsDialog(QDialog):
    def __init__(self, record_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("실시간 구간 기록 확인")
        self.resize(1000, 660)
        self.setMinimumSize(560, 440)
        layout = QVBoxLayout(self)
        self.records = LiveRecordsWidget(record_path, self)
        layout.addWidget(self.records)
