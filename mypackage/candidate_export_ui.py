"""A modal, responsive photo export shared by results and reopened records."""

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout

from mypackage.candidate_export import EXPORT_FILENAME, export_photo_candidates


class CandidateExportJob(QThread):
    def __init__(self, record_path, destination, parent=None):
        super().__init__(parent)
        self.record_path, self.destination = record_path, destination
        self.payload, self.error = None, None

    def run(self):
        try:
            self.payload = export_photo_candidates(self.record_path, self.destination)
        except Exception as error:
            self.error = str(error)


class CandidateExportProgress(QDialog):
    def reject(self):
        if not self.job.isRunning():
            super().reject()

    def closeEvent(self, event):
        if self.job.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)


def choose_photo_export(parent, record_path):
    record_path = Path(record_path)
    destination, _ = QFileDialog.getSaveFileName(
        parent, "상황판용 사진 후보 내보내기", str(record_path.parent / EXPORT_FILENAME), "JSON (*.json)"
    )
    if not destination:
        return None
    dialog = CandidateExportProgress(parent)
    dialog.setWindowTitle("상황판용 사진 후보 내보내기")
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("후보 파일을 만드는 중입니다. 완료될 때까지 기다려 주세요."))
    bar = QProgressBar()
    bar.setRange(0, 0)
    layout.addWidget(bar)
    dialog.job = CandidateExportJob(record_path, Path(destination), dialog)
    dialog.job.finished.connect(dialog.accept)
    app = QApplication.instance()
    app.aboutToQuit.connect(dialog.job.wait)
    dialog.job.start()
    dialog.exec()
    dialog.job.wait()
    app.aboutToQuit.disconnect(dialog.job.wait)
    if dialog.job.error:
        QMessageBox.warning(parent, "후보 내보내기 실패", dialog.job.error)
        return None
    payload = dialog.job.payload
    missing = sum(c["thumbnail"] is None for c in payload["candidates"])
    QMessageBox.information(
        parent, "상황판용 파일 저장됨",
        f"후보 {len(payload['candidates'])}건 · 미리보기 없음 {missing}건\n{destination}\n\n"
        "STAY UP의 AI 후보 불러오기로 추가·갱신하세요. GPS는 사진 촬영 위치입니다."
    )
    return destination
