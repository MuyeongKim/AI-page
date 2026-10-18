"""A modal, responsive photo export shared by results and reopened records."""

from pathlib import Path
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout

from mypackage.candidate_export import EXPORT_FILENAME, export_photo_candidates


class CandidateExportJob(QThread):
    def __init__(self, record_path, destination, parent=None, *, to_folder=False, cancelled=None):
        super().__init__(parent)
        self.record_path, self.destination = record_path, destination
        self.payload, self.error = None, None
        self.options = {"to_folder": to_folder, "cancelled": cancelled} if to_folder else {}

    def run(self):
        try:
            self.payload = export_photo_candidates(self.record_path, self.destination, **self.options)
        except Exception as error:
            self.error = str(error)


class CandidateFolderPublisher(QObject):
    """Session-only, serial background exports; repeated saved edits coalesce."""

    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder, self.job = None, None
        self.pending = {}
        self.cancelled = threading.Event()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._start)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def connect_folder(self, folder):
        self.disconnect_folder()
        folder = Path(folder).resolve()
        if not folder.is_dir():
            raise OSError("연결할 폴더를 찾을 수 없습니다.")
        self.folder, self.cancelled = folder, threading.Event()
        self.status_changed.emit(f"자동 저장 연결 · {folder}\n사진 분석 종료·판정 저장 시 갱신합니다.")

    def disconnect_folder(self):
        self.cancelled.set()
        self.folder = None
        self.pending.clear()
        self.timer.stop()
        self.status_changed.emit("자동 저장 연결 안 됨 · 수동 내보내기는 계속 사용할 수 있습니다.")

    def request(self, record_path):
        if self.folder is None or not record_path:
            return
        self.pending[str(Path(record_path).resolve())] = 0
        self.timer.start(150)

    def _start(self):
        if self.job is not None or self.folder is None or not self.pending:
            return
        path = next(iter(self.pending))
        attempts = self.pending.pop(path)
        self.job = CandidateExportJob(path, self.folder, self, to_folder=True, cancelled=self.cancelled)
        self.job.attempts = attempts
        self.job.finished.connect(self._finished)
        self.status_changed.emit(f"자동 저장 중 · {self.folder}")
        self.job.start()

    def _finished(self):
        job, self.job = self.job, None
        if not job.options["cancelled"].is_set():
            if job.error:
                self.status_changed.emit(f"자동 저장 실패 · {job.error}\n연결 폴더: {self.folder}")
                if job.attempts < 2 and job.record_path not in self.pending:
                    self.pending[job.record_path] = job.attempts + 1
            else:
                run = job.payload["run"]
                self.status_changed.emit(
                    f"자동 저장 완료 · 작업 {run['id'][:8]} · 리비전 {run['revision']}\n{self.folder}"
                )
        job.deleteLater()
        if self.pending:
            self.timer.start(2000 if job.error else 150)

    def shutdown(self):
        self.disconnect_folder()
        if self.job is not None:
            self.job.wait()


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
