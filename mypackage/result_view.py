"""Synchronized photo comparison with bounded previews and native-resolution regions."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImageIOHandler, QImageReader, QKeySequence, QPainter, QPen, QShortcut, QTransform
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

PREVIEW_EDGE = 1800
MAX_FALLBACK_PIXELS = 24_000_000
MAX_REGION_PIXELS = 8_000_000


class PhotoPreview(QWidget):
    """Render a small overview, then replace visible pixels from the source file."""

    view_changed = Signal(float, object)
    resized = Signal()

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleDescription(
            "마우스 휠 또는 더하기·빼기로 확대하고 드래그 또는 방향키로 이동합니다."
        )
        self.source_size = QSize()
        self._raw_size = QSize()
        self.zoom = 1.0
        self.center = QPointF(0.5, 0.5)
        self.fit_mode = True
        self._preview = None
        self._detail = None
        self._detail_rect = QRect()
        self._drag_position = None
        self._error = ""
        self._region_error = ""
        self._raw_to_display = QTransform()
        self.highlight_box = None
        self._detail_timer = QTimer(self)
        self._detail_timer.setSingleShot(True)
        self._detail_timer.setInterval(100)
        self._detail_timer.timeout.connect(self._load_visible_region)
        self._load_preview()

    def _reader(self):
        reader = QImageReader(self.path)
        reader.setAutoTransform(True)
        return reader

    def _load_preview(self):
        reader = self._reader()
        raw_size = reader.size()
        if not raw_size.isValid():
            self._error = "사진을 읽을 수 없습니다. 저장 폴더에서 원본을 확인해 주세요."
            return
        pixels = raw_size.width() * raw_size.height()
        native_clip = reader.supportsOption(QImageIOHandler.ImageOption.ClipRect)
        native_scale = reader.supportsOption(QImageIOHandler.ImageOption.ScaledSize)
        if pixels > MAX_FALLBACK_PIXELS and not (native_clip and native_scale):
            self._error = (
                "이 형식의 큰 사진은 메모리 보호를 위해 비교창에서 열 수 없습니다. "
                "저장 폴더에서 원본을 확인해 주세요."
            )
            return

        width, height = raw_size.width(), raw_size.height()
        self._raw_size = raw_size
        orientation = reader.transformation().value
        transforms = {
            0: QTransform(),
            1: QTransform(-1, 0, 0, 1, width, 0),
            2: QTransform(1, 0, 0, -1, 0, height),
            3: QTransform(-1, 0, 0, -1, width, height),
            4: QTransform(0, 1, -1, 0, height, 0),
            5: QTransform(0, -1, -1, 0, height, width),
            6: QTransform(0, 1, 1, 0, 0, 0),
            7: QTransform(0, -1, 1, 0, 0, width),
        }
        self._raw_to_display = transforms[orientation]
        self.source_size = QSize(height, width) if orientation & 4 else raw_size
        if max(width, height) > PREVIEW_EDGE:
            reader.setScaledSize(raw_size.scaled(
                QSize(PREVIEW_EDGE, PREVIEW_EDGE), Qt.AspectRatioMode.KeepAspectRatio
            ))
        image = reader.read()
        if image.isNull():
            self._error = "사진을 읽을 수 없습니다. 손상 여부와 파일 형식을 확인해 주세요."
            return
        image.setDevicePixelRatio(1)
        self._preview = image

    def fit_zoom(self):
        if not self.source_size.isValid():
            return 1.0
        return min(
            1.0, self.width() / self.source_size.width(),
            self.height() / self.source_size.height(),
        )

    def set_view(self, zoom=None, center=None):
        self.fit_mode = zoom is None
        self.zoom = self.fit_zoom() if self.fit_mode else min(16.0, max(0.005, zoom))
        self.center = QPointF(center) if center is not None else QPointF(0.5, 0.5)
        self._clamp_center()
        self._detail = None
        self._detail_rect = QRect()
        self._region_error = ""
        self._detail_timer.start()
        self.update()

    def _clamp_center(self):
        if not self.source_size.isValid():
            return
        coordinates = []
        for extent, viewport, requested in (
            (self.source_size.width(), self.width(), self.center.x()),
            (self.source_size.height(), self.height(), self.center.y()),
        ):
            half_visible = min(0.5, viewport / (2 * extent * self.zoom))
            coordinates.append(min(1 - half_visible, max(half_visible, requested)))
        self.center = QPointF(*coordinates)

    def image_origin(self):
        return QPointF(
            self.width() / 2 - self.center.x() * self.source_size.width() * self.zoom,
            self.height() / 2 - self.center.y() * self.source_size.height() * self.zoom,
        )

    def visible_source_rect(self):
        if not self.source_size.isValid():
            return QRect()
        origin = self.image_origin()
        viewport = QRectF(
            -origin.x() / self.zoom, -origin.y() / self.zoom,
            self.width() / self.zoom, self.height() / self.zoom,
        ).toAlignedRect()
        return viewport.intersected(QRect(QPointF(0, 0).toPoint(), self.source_size))

    def _load_visible_region(self):
        if self._preview is None or not self.source_size.isValid():
            return
        if self.zoom <= self._preview.width() / self.source_size.width():
            return
        display_rect = self.visible_source_rect()
        if display_rect.isEmpty():
            return
        inverse, _ = self._raw_to_display.inverted()
        raw_rect = inverse.mapRect(QRectF(display_rect)).toAlignedRect()
        reader = self._reader()
        if reader.size() != self._raw_size:
            self._region_error = "사진 파일이 변경되었습니다. 비교창을 닫고 다시 열어 주세요."
            self.update()
            return
        reader.setClipRect(raw_rect)
        # Qt clips before scaling and applies EXIF orientation after decoding.
        scale = min(1.0, self.zoom)
        read_size = QSize(
            max(1, math.ceil(raw_rect.width() * scale)),
            max(1, math.ceil(raw_rect.height() * scale)),
        )
        if read_size.width() * read_size.height() > MAX_REGION_PIXELS:
            self._region_error = "표시 영역이 너무 큽니다. 비교창 크기를 줄여 다시 확인해 주세요."
            self.update()
            return
        if scale < 1.0:
            reader.setScaledSize(read_size)
        detail = reader.read()
        if detail.isNull():
            self._region_error = "원본 영역을 읽지 못했습니다. 저장 폴더에서 파일을 확인해 주세요."
        else:
            detail.setDevicePixelRatio(1)
            self._detail = detail
            self._detail_rect = display_rect
            self._region_error = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111827"))
        if self._preview is None or self._region_error:
            painter.setPen(QColor("#f8fafc"))
            painter.drawText(
                self.rect().adjusted(14, 14, -14, -14),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self._region_error or self._error,
            )
            return
        origin = self.image_origin()
        target = QRectF(
            origin.x(), origin.y(),
            self.source_size.width() * self.zoom, self.source_size.height() * self.zoom,
        )
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom < 1)
        painter.drawImage(target, self._preview)
        if self._detail is not None:
            region = self._detail_rect
            painter.drawImage(QRectF(
                origin.x() + region.x() * self.zoom, origin.y() + region.y() * self.zoom,
                region.width() * self.zoom, region.height() * self.zoom,
            ), self._detail)
        elif self.zoom > self._preview.width() / self.source_size.width():
            painter.fillRect(QRect(0, 0, self.width(), 28), QColor("#134e4a"))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(QRect(8, 0, self.width() - 16, 28),
                             Qt.AlignmentFlag.AlignVCenter, "원본 영역을 불러오는 중…")
        if self.highlight_box is not None:
            x1, y1, x2, y2 = self.highlight_box
            painter.setPen(QPen(QColor("#ffcc33"), 2))
            painter.drawRect(QRectF(origin.x() + x1 * self.zoom, origin.y() + y1 * self.zoom,
                                    (x2 - x1) * self.zoom, (y2 - y1) * self.zoom))
        if self.hasFocus():
            painter.setPen(QColor("#5eead4"))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.set_view(None if self.fit_mode else self.zoom, self.center)
        self.resized.emit()

    def request_zoom(self, factor, anchor=None):
        if not self.source_size.isValid() or self._preview is None:
            return
        if anchor is None:
            anchor = QPointF(self.width() / 2, self.height() / 2)
        old_origin = self.image_origin()
        source_point = (anchor - old_origin) / self.zoom
        zoom = min(16.0, max(0.005, self.zoom * factor))
        center = QPointF(
            (source_point.x() - (anchor.x() - self.width() / 2) / zoom)
            / self.source_size.width(),
            (source_point.y() - (anchor.y() - self.height() / 2) / zoom)
            / self.source_size.height(),
        )
        self.view_changed.emit(zoom, center)

    def pan(self, delta):
        if not self.source_size.isValid() or self._preview is None:
            return
        center = QPointF(
            self.center.x() - delta.x() / (self.zoom * self.source_size.width()),
            self.center.y() - delta.y() / (self.zoom * self.source_size.height()),
        )
        self.view_changed.emit(self.zoom, center)

    def wheelEvent(self, event):
        amount = event.angleDelta().y() or event.pixelDelta().y()
        if amount:
            self.request_zoom(1.25 if amount > 0 else 0.8, event.position())
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None:
            delta = event.position() - self._drag_position
            self._drag_position = event.position()
            self.pan(delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        directions = {
            Qt.Key.Key_Left: QPointF(60, 0), Qt.Key.Key_Right: QPointF(-60, 0),
            Qt.Key.Key_Up: QPointF(0, 60), Qt.Key.Key_Down: QPointF(0, -60),
        }
        if event.key() in directions:
            self.pan(directions[event.key()])
            event.accept()
        else:
            super().keyPressEvent(event)


class ResultComparisonDialog(QDialog):
    current_changed = Signal(int)

    def __init__(self, original, detected, parent=None, *, items=None, current_index=0, comparison=True):
        super().__init__(parent)
        self.items = list(items) if items else [{"original": original, "output": detected}]
        self.current_index = max(0, min(current_index, len(self.items) - 1))
        self.comparison_mode = comparison
        self.setWindowTitle("원본과 탐지 결과 비교")
        self.resize(1050, 680)
        self.setMinimumSize(500, 360)
        self.setStyleSheet("""
            QDialog { background: #f4efe7; }
            QLabel { color: #1f2937; }
            QPushButton {
                background: #fffdf9; color: #0f3d3a; border: 1px solid #d9cbb8;
                border-radius: 7px; padding: 0 8px;
            }
            QPushButton:hover { background: #e5f3ef; }
            QPushButton:focus { border: 2px solid #0f766e; }
            QPushButton:disabled { color: #7c838e; background: #eee7dd; }
        """)
        layout = QVBoxLayout(self)
        notice = QLabel(
            "표시된 영역은 탐지 후보입니다. 원본과 비교해 직접 확인하세요.\n"
            "휠로 확대·축소, 드래그 또는 방향키로 이동하면 양쪽 사진이 함께 움직입니다."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton("← 이전 사진")
        self.next_button = QPushButton("다음 사진 →")
        self.item_label = QLabel()
        self.item_label.setTextFormat(Qt.TextFormat.PlainText)
        self.item_label.setWordWrap(True)
        self.mode_button = QPushButton()
        for button in (self.previous_button, self.next_button, self.mode_button):
            button.setMinimumHeight(40)
            button.setAutoDefault(False)
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.item_label, 1)
        navigation.addWidget(self.next_button)
        navigation.addWidget(self.mode_button)
        layout.addLayout(navigation)
        self.previous_button.clicked.connect(lambda: self.move_photo(-1))
        self.next_button.clicked.connect(lambda: self.move_photo(1))
        self.mode_button.clicked.connect(self.toggle_mode)
        for sequence, delta in (("PgUp", -1), ("PgDown", 1), ("Alt+Left", -1), ("Alt+Right", 1)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda delta=delta: self.move_photo(delta))
        toolbar = QHBoxLayout()
        self.zoom_out_button = QPushButton("− 축소")
        self.zoom_in_button = QPushButton("+ 확대")
        self.actual_size_button = QPushButton("100% 보기")
        self.fit_button = QPushButton("화면 맞춤")
        for button, description, shortcut in (
            (self.zoom_out_button, "양쪽 사진 축소", "-"),
            (self.zoom_in_button, "양쪽 사진 확대", "+"),
            (self.actual_size_button, "원본 해상도 100퍼센트 보기", "1"),
            (self.fit_button, "사진 전체를 화면에 맞추기", "Home"),
        ):
            button.setAccessibleName(description)
            button.setToolTip(f"{description} ({shortcut})")
            button.setMinimumHeight(36)
            button.setAutoDefault(False)
            toolbar.addWidget(button)
        self.zoom_label = QLabel("화면 맞춤")
        self.zoom_label.setAccessibleName("현재 비교 배율")
        toolbar.addWidget(self.zoom_label)
        layout.addLayout(toolbar)
        self.columns = QHBoxLayout()
        self.previews = []
        self.photo_columns = []
        layout.addLayout(self.columns, 1)
        self.zoom_out_button.clicked.connect(lambda: self.primary_preview().request_zoom(0.8))
        self.zoom_in_button.clicked.connect(lambda: self.primary_preview().request_zoom(1.25))
        self.actual_size_button.clicked.connect(
            lambda: self._sync_view(1.0, self.primary_preview().center)
        )
        self.fit_button.clicked.connect(self.fit_to_window)
        self.load_photo()

    def load_photo(self):
        for preview in self.previews:
            preview._detail_timer.stop()
        while self.columns.count():
            item = self.columns.takeAt(0)
            item.widget().hide()
            item.widget().deleteLater()
        self.previews = []
        self.photo_columns = []
        item = self.items[self.current_index]
        self.item_label.setText(
            f"사진 {self.current_index + 1} / {len(self.items)} · {Path(item['output']).name}"
        )
        self.previous_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index + 1 < len(self.items))
        for title, path in (("원본", item.get("original")), ("탐지 결과", item["output"])):
            wrapper = QWidget()
            column = QVBoxLayout(wrapper)
            column.setContentsMargins(0, 0, 0, 0)
            label = QLabel(f"{title} · {Path(path).name if path else '파일 없음'}")
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            label.setToolTip(str(path or "파일 없음"))
            column.addWidget(label)
            preview = PhotoPreview(path or "")
            preview.setAccessibleName(f"{title} 사진")
            preview.view_changed.connect(self._sync_view)
            preview.resized.connect(self._update_zoom_label)
            self.previews.append(preview)
            column.addWidget(preview, 1)
            self.columns.addWidget(wrapper, 1)
            self.photo_columns.append(wrapper)
        self.update_mode()
        self.fit_to_window()

    def primary_preview(self):
        return self.previews[0 if self.comparison_mode else 1]

    def update_mode(self):
        self.photo_columns[0].setVisible(self.comparison_mode)
        self.mode_button.setText("탐지본만 보기" if self.comparison_mode else "원본과 비교")
        self.setWindowTitle("원본과 탐지 결과 비교" if self.comparison_mode else "탐지 결과 사진 보기")
        available = all(preview._preview is not None for preview in
                        (self.previews if self.comparison_mode else self.previews[1:]))
        for button in (
            self.zoom_out_button, self.zoom_in_button, self.actual_size_button, self.fit_button
        ):
            button.setEnabled(available)

    def toggle_mode(self):
        self.comparison_mode = not self.comparison_mode
        self.update_mode()
        self.fit_to_window()

    def move_photo(self, delta):
        index = self.current_index + delta
        if not 0 <= index < len(self.items):
            return
        self.current_index = index
        self.load_photo()
        self.current_changed.emit(index)

    def _sync_view(self, zoom, center):
        for preview in self.previews:
            preview.set_view(zoom, center)
        self._update_zoom_label()

    def _update_zoom_label(self):
        if not self.previews:
            return
        preview = self.primary_preview()
        self.zoom_label.setText("화면 맞춤" if preview.fit_mode else f"{preview.zoom * 100:.0f}%")

    def fit_to_window(self):
        for preview in self.previews:
            preview.set_view()
        self._update_zoom_label()

    def keyPressEvent(self, event):
        actions = {
            Qt.Key.Key_Plus: self.zoom_in_button,
            Qt.Key.Key_Equal: self.zoom_in_button,
            Qt.Key.Key_Minus: self.zoom_out_button,
            Qt.Key.Key_1: self.actual_size_button,
            Qt.Key.Key_Home: self.fit_button,
        }
        button = actions.get(event.key())
        if button is not None:
            button.click()
            event.accept()
        else:
            super().keyPressEvent(event)
