"""Bounded, side-by-side preview of an original photo and its detection result."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout


class PhotoPreview(QLabel):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(100, 100)
        self.setStyleSheet("background: #111827; color: #f8fafc; border-radius: 8px;")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and max(size.width(), size.height()) > 1800:
            reader.setScaledSize(size.scaled(QSize(1800, 1800), Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        self._photo = QPixmap.fromImage(image) if not image.isNull() else None
        if self._photo is None:
            self.setText("사진을 읽을 수 없습니다. 저장 폴더에서 파일을 확인해 주세요.")
            self.setWordWrap(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._photo is not None:
            self.setPixmap(self._photo.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))


class ResultComparisonDialog(QDialog):
    def __init__(self, original, detected, parent=None):
        super().__init__(parent)
        self.setWindowTitle("원본과 탐지 결과 비교")
        self.resize(1050, 620)
        self.setMinimumSize(500, 360)
        layout = QVBoxLayout(self)
        notice = QLabel("표시된 영역은 탐지 후보입니다. 원본과 비교해 직접 확인하세요.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        columns = QHBoxLayout()
        for title, path in (("원본", original), ("탐지 결과", detected)):
            column = QVBoxLayout()
            label = QLabel(f"{title} · {Path(path).name}")
            label.setWordWrap(True)
            column.addWidget(label)
            preview = PhotoPreview(path)
            preview.setAccessibleName(f"{title} 사진")
            column.addWidget(preview, 1)
            columns.addLayout(column, 1)
        layout.addLayout(columns, 1)
