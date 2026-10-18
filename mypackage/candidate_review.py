"""Keyboard-first review of individual photo candidates without altering source images."""

from collections import Counter
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from mypackage.detection_records import (
    REVIEW_LABELS, asset_path, load_detections, save_photo_review,
)
from mypackage.result_view import PhotoPreview, ResultComparisonDialog
from mypackage.search_report import create_search_report


class CandidateReviewDialog(QDialog):
    changed = Signal()

    def __init__(self, record_path, parent=None):
        super().__init__(parent)
        self.path = Path(record_path)
        self.document = load_detections(self.path)
        self.entries = self._entries()
        self.index = 0
        self.preview = None
        self.comparison = None
        self.setWindowTitle("사람 후보 확인")
        self.resize(920, 700)
        self.setMinimumSize(520, 440)
        self.setStyleSheet("""
            QDialog { background: #f4efe7; }
            QLabel { color: #1f2937; font-size: 13px; }
            QPushButton { background: #fffdf9; color: #134e4a; border: 1px solid #c1d2ce;
                          border-radius: 6px; padding: 0 6px; }
            QPushButton:focus { border: 2px solid #0f766e; }
            QPushButton:disabled { color: #6b7280; background: #e5e7eb; }
        """)
        layout = QVBoxLayout(self)
        notice = QLabel("후보별로 원본을 확인하세요. 후보 수는 고유 인원이 아니며 GPS는 촬영 위치입니다.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.candidate_label = QLabel()
        self.candidate_label.setTextFormat(Qt.TextFormat.PlainText)
        self.candidate_label.setWordWrap(True)
        layout.addWidget(self.candidate_label)
        self.photo_area = QWidget()
        self.photo_layout = QVBoxLayout(self.photo_area)
        self.photo_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.photo_area, 1)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton("← 이전")
        self.next_button = QPushButton("다음 →")
        self.compare_button = QPushButton("원본과 비교")
        self.actual_button = QPushButton("100% 보기")
        for button in (self.previous_button, self.next_button, self.compare_button, self.actual_button):
            button.setMinimumHeight(36)
            button.setAutoDefault(False)
            button.setAccessibleName(button.text())
            navigation.addWidget(button)
        layout.addLayout(navigation)
        judgments = QHBoxLayout()
        self.review_buttons = []
        for key, review in (("1", "person"), ("2", "false_positive"), ("3", "hold")):
            button = QPushButton(f"{key} · {REVIEW_LABELS[review]}")
            button.setMinimumHeight(40)
            button.setAutoDefault(False)
            button.setAccessibleName(f"현재 후보 {REVIEW_LABELS[review]}로 저장")
            button.clicked.connect(lambda _checked=False, state=review: self.set_review(state))
            judgments.addWidget(button)
            self.review_buttons.append(button)
            self._shortcut(key, lambda state=review: self.set_review(state))
        layout.addLayout(judgments)
        self.report_button = QPushButton("보고서 만들고 열기")
        self.report_button.setMinimumHeight(36)
        self.report_button.setAccessibleName("현재 판정으로 오프라인 HTML 보고서를 만들고 열기")
        self.report_button.clicked.connect(self.open_report)
        layout.addWidget(self.report_button)
        self.save_status = QLabel("판정은 즉시 기록 파일에 저장합니다. ←/→ 이동, 1/2/3 판정")
        self.save_status.setTextFormat(Qt.TextFormat.PlainText)
        self.save_status.setWordWrap(True)
        layout.addWidget(self.save_status)
        self.previous_button.clicked.connect(lambda: self.move(-1))
        self.next_button.clicked.connect(lambda: self.move(1))
        self.compare_button.clicked.connect(self.compare)
        self.actual_button.clicked.connect(self.actual_size)
        self._shortcut("Left", lambda: self.move(-1))
        self._shortcut("Right", lambda: self.move(1))
        self._focus_timer = QTimer(self)
        self._focus_timer.setSingleShot(True)
        self._focus_timer.timeout.connect(self.focus_candidate)
        self.render_candidate()

    def _shortcut(self, sequence, callback):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(callback)

    def _entries(self):
        return [(photo, candidate) for photo in self.document["photos"] for candidate in photo["people"]]

    def move(self, delta):
        if self.entries:
            self.index = max(0, min(len(self.entries) - 1, self.index + delta))
            self.render_candidate()

    def render_candidate(self):
        while self.photo_layout.count():
            item = self.photo_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.preview = None
        for button in self.review_buttons:
            button.setEnabled(bool(self.entries))
        self.previous_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index + 1 < len(self.entries))
        self.compare_button.setEnabled(False)
        self.actual_button.setEnabled(False)
        if not self.entries:
            self.candidate_label.setText("기록된 사람 후보가 없습니다. 처리 실패와 미탐지는 보고서에서 확인하세요.")
            return
        photo, candidate = self.entries[self.index]
        counts = Counter(c["review"] for _, c in self.entries)
        gps = photo.get("gps")
        location = f"촬영 위치 {gps['lat']:.6f}, {gps['lon']:.6f}" if gps else "촬영 위치 없음"
        self.candidate_label.setText(
            f"후보 {self.index + 1}/{len(self.entries)} · {Path(photo.get('source', '')).name}\n"
            f"{candidate['id']} · 신뢰도 {candidate['confidence']:.1%} · "
            f"{REVIEW_LABELS[candidate['review']]} · {location}\n"
            f"사람 맞음 {counts['person']} · 오탐 {counts['false_positive']} · "
            f"보류 {counts['hold']} · 미확인 {counts['unreviewed']}"
        )
        original = asset_path(self.path.parent, photo.get("original_file"))
        detected = asset_path(self.path.parent, photo.get("detected_file"))
        if original and original.is_file():
            self.preview = PhotoPreview(original)
            self.preview.highlight_box = candidate["box"]
            self.preview.setAccessibleName("현재 사람 후보 원본 확대")
            self.photo_layout.addWidget(self.preview)
            self.actual_button.setEnabled(self.preview._preview is not None)
            self.compare_button.setEnabled(bool(detected and detected.is_file()))
            self._focus_timer.start(0)
        else:
            self.photo_layout.addWidget(QLabel("원본 사진을 찾을 수 없습니다. 저장 폴더를 확인하세요."))

    def focus_candidate(self):
        if self.preview is None or not self.preview.source_size.isValid():
            return
        photo, candidate = self.entries[self.index]
        width, height = photo["image_size"]
        if (self.preview.source_size.width(), self.preview.source_size.height()) != (width, height):
            self.save_status.setText("원본 크기가 기록과 다릅니다. 원본이 바뀌었는지 확인하세요.")
            return
        x1, y1, x2, y2 = candidate["box"]
        zoom = min(self.preview.width() / max(96, (x2 - x1) * 3),
                   self.preview.height() / max(96, (y2 - y1) * 3))
        self.preview.set_view(min(16, zoom), QPointF((x1 + x2) / (2 * width),
                                                    (y1 + y2) / (2 * height)))

    def actual_size(self):
        if self.preview is not None:
            self.preview.set_view(1.0, self.preview.center)

    def set_review(self, review):
        if not self.entries:
            return
        candidate_id = self.entries[self.index][1]["id"]
        try:
            self.document = save_photo_review(self.path, candidate_id, review)
            self.entries = self._entries()
            self.index = next(i for i, (_, candidate) in enumerate(self.entries)
                              if candidate["id"] == candidate_id)
            self.render_candidate()
            self.save_status.setText(f"저장됨 · {candidate_id} · {REVIEW_LABELS[review]}")
            self.changed.emit()
        except Exception as error:
            self.save_status.setText(f"저장 실패 · 판정은 변경되지 않았습니다: {error}")
            return
        try:
            create_search_report(self.path)
        except Exception as error:
            self.save_status.setText(f"판정은 저장됨 · 보고서 갱신 실패: {error}")

    def open_report(self):
        try:
            path = create_search_report(self.path)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
                raise OSError("브라우저를 열지 못했습니다. 저장 폴더에서 보고서를 확인하세요.")
            self.save_status.setText("현재 판정으로 보고서를 저장했습니다.")
        except Exception as error:
            self.save_status.setText(f"보고서 생성·열기 실패: {error}")

    def compare(self):
        if not self.entries:
            return
        photo, _ = self.entries[self.index]
        original = asset_path(self.path.parent, photo.get("original_file"))
        detected = asset_path(self.path.parent, photo.get("detected_file"))
        if original and detected and original.is_file() and detected.is_file():
            if self.comparison is not None:
                self.comparison.close()
                self.comparison.deleteLater()
            self.comparison = ResultComparisonDialog(original, detected, self)
            self.comparison.show()
