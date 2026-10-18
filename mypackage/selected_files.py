"""Review a photo selection without parsing editable, comma-separated paths."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)


class SelectedFilesDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("선택한 사진")
        self.resize(640, 420)
        self.setStyleSheet("""
            QDialog { background: #f4efe7; }
            QLabel { color: #134e4a; font-size: 13px; padding: 4px; }
            QListWidget { background: white; border: 1px solid #c1d2ce; padding: 6px; }
            QListWidget::item { min-height: 30px; }
            QListWidget::item:selected { background: #dff0ea; color: #134e4a; }
            QPushButton { min-height: 32px; padding: 0 12px; border: 1px solid #c1d2ce;
                          border-radius: 6px; background: #fffdf9; color: #134e4a; }
            QPushButton:focus, QListWidget:focus { border: 2px solid #0f766e; }
            QPushButton:disabled { color: #6b7280; background: #e5e7eb; }
        """)
        layout = QVBoxLayout(self)
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self.files_list = QListWidget()
        self.files_list.setAccessibleName("선택한 사진 목록")
        self.files_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.files_list.addItems([str(path) for path in paths])
        for row in range(self.files_list.count()):
            item = self.files_list.item(row)
            item.setToolTip(item.text())
        layout.addWidget(self.files_list, 1)
        self.remove_button = QPushButton("선택 항목 제외")
        self.remove_button.setToolTip("목록에서만 제외합니다. 원본 파일은 삭제하지 않습니다.")
        self.remove_button.clicked.connect(self.remove_selected)
        self.files_list.itemSelectionChanged.connect(self.update_count)
        layout.addWidget(self.remove_button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("적용")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_count()

    def selected_paths(self):
        return [self.files_list.item(row).text() for row in range(self.files_list.count())]

    def remove_selected(self):
        for item in self.files_list.selectedItems():
            self.files_list.takeItem(self.files_list.row(item))
        self.update_count()

    def update_count(self):
        self.count_label.setText(f"사진 {self.files_list.count()}장 · 제외 후 적용을 누르세요.")
        self.remove_button.setEnabled(bool(self.files_list.selectedItems()))
