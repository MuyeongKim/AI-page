###############################################################################################
#  ______     __                                  __    __                   ______   ______  #
# /      \   /  |                                /  |  /  |                 /      \ /      | #
# /$$$$$$  | _$$ |_     ______   __    __         $$ |  $$ |  ______        /$$$$$$  |$$$$$$/  #
# $$ \__$$/ / $$   |   /      \ /  |  /  | ______ $$ |  $$ | /      \       $$ |__$$ |  $$ |   #
# $$      \ $$$$$$/    $$$$$$  |$$ |  $$ |/      |$$ |  $$ |/$$$$$$  |      $$    $$ |  $$ |   #
# $$$$$$  |  $$ | __  /    $$ |$$ |  $$ |$$$$$$/ $$ |  $$ |$$ |  $$ |      $$$$$$$$ |  $$ |   #
# /  \__$$ |  $$ |/  |/$$$$$$$ |$$ \__$$ |        $$ \__$$ |$$ |__$$ |      $$ |  $$ | _$$ |_  #
# $$    $$/   $$  $$/ $$    $$ |$$    $$ |        $$    $$/ $$    $$/       $$ |  $$ |/ $$   | #
# $$$$$$/     $$$$/   $$$$$$$/  $$$$$$$ |         $$$$$$/  $$$$$$$/        $$/   $$/ $$$$$$/  #
#                              /  \__$$ |                  $$ |                               #
#                              $$    $$/                   $$ |                               #
#                               $$$$$$/                    $$/                                #
#                                                                                             #
###############################################################################################
# -----------------------------------------------------------------------------
# 🚀 메모리 최적화 업데이트 (2025.08.10)
# - 메모리 모니터링 시스템 통합 (memory_monitor.py)
# - FPS 버퍼를 collections.deque로 최적화 (O(1) 성능)
# - 실시간 처리 루프에 주기적 메모리 정리 추가 (100프레임마다)
# - 프로그램 종료 시 메모리 사용량 요약 출력
# - 매 프레임마다 YOLO 결과 객체 즉시 해제로 메모리 누수 방지
# -----------------------------------------------------------------------------


import gc  # 가비지 컬렉터 추가
import math
import os
import platform
import shutil
import sys
import threading
import time
from collections import deque  # 메모리 효율적인 FPS 버퍼용
from pathlib import Path
from uuid import uuid4

import cv2  # OpenCV 추가
import numpy as np  # Numpy 추가
import torch
from PySide6.QtCore import QSettings, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ultralytics import YOLO

from mypackage import gps2, start
from mypackage.device import get_preferred_device, is_mps_available
from mypackage.modern_gui_fixed import ModernUi_MainWindow
from mypackage.notices import NOTICE_SOURCE_CACHE, NoticeLoadResult, OnlineNoticeLoader
from mypackage.video_source import (
    CAPTURE_BOARD_SOURCE,
    VIDEO_FILE_SOURCE,
    is_live_video_source,
    normalize_source_name,
    resolve_video_source_path,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DETECTED_OUTPUT_DIR = PROJECT_ROOT / "detected_files"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"}
PERSON_AND_VEHICLE_CLASSES = [0, 2, 5, 7]
PREVIEW_REFRESH_INTERVAL_MS = 50  # 20 FPS; detection and output writing remain unthrottled.
VIDEO_END_TOLERANCE_MS = 50
DETECTION_STATUS_COMPLETED = "completed"
DETECTION_STATUS_PARTIAL = "partial"
DETECTION_STATUS_FAILED = "failed"
DETECTION_STATUS_CANCELLED = "cancelled"
DETECTION_STATUS_DISCONNECTED = "disconnected"
RESULT_FOLDER_STATUSES = frozenset(
    {DETECTION_STATUS_COMPLETED, DETECTION_STATUS_PARTIAL}
)
NOTICE_SETTINGS_ORGANIZATION = "StayUpAI"
NOTICE_SETTINGS_APPLICATION = "AIObjectDetection"
NOTICE_SETTINGS_REVISION_KEY = "online_news/last_seen_revision"
NOTICE_TAB_TITLE = "온라인 소식"
NOTICE_TAB_UNREAD_TITLE = "온라인 소식 · 새 글"
NOTICE_KIND_LABELS = {
    "notice": "공지",
    "release": "업데이트",
    "maintenance": "점검",
}


def resolve_model_source(model_source):
    """Resolve bundled models from the project root and preserve download aliases."""
    if not model_source:
        raise ValueError("탐지 모델을 선택해 주세요.")

    candidate = Path(str(model_source)).expanduser()
    if candidate.is_absolute():
        return str(candidate)

    bundled_candidate = PROJECT_ROOT / candidate
    if bundled_candidate.exists():
        return str(bundled_candidate)

    # Ultralytics model aliases such as yolo11n.pt may be downloaded on demand.
    return str(model_source)


# 메모리 모니터링 도구 import
try:
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from memory_monitor import MemoryMonitor

    MEMORY_MONITOR_AVAILABLE = True
    print("✅ 메모리 모니터링 활성화")
except ImportError:
    print("⚠️ 메모리 모니터링 비활성화 (memory_monitor.py 없음)")
    MEMORY_MONITOR_AVAILABLE = False

    class MemoryMonitor:
        def __init__(self):
            pass

        def log_memory_usage(self, context=""):
            pass

        def get_summary(self):
            return "모니터링 비활성화"


def clear_torch_cache(device=None):
    """현재 장치에 맞는 PyTorch 캐시 정리."""
    if (device in (None, "cuda")) and torch.cuda.is_available():
        torch.cuda.empty_cache()

    if (
        device in (None, "mps")
        and is_mps_available()
        and hasattr(torch, "mps")
        and hasattr(torch.mps, "empty_cache")
    ):
        torch.mps.empty_cache()


class PreviewWindow(QWidget):
    """실시간 탐지 프레임을 표시하는 별도 Qt 창."""

    close_requested = Signal()

    def __init__(self):
        super().__init__()
        self._closing_programmatically = False
        self.preview_pixmap = None

        self.setWindowTitle("실시간 탐지 미리보기")
        self.resize(1100, 760)
        self.setMinimumSize(720, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.status_label = QLabel("실시간 입력을 시작하면 미리보기가 표시됩니다.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_label)

        self.preview_label = QLabel("Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            """
            QLabel {
                border: 1px solid #2f3e46;
                border-radius: 14px;
                background: #111827;
                color: rgba(248, 250, 252, 0.72);
                font-size: 24px;
                font-weight: 700;
            }
            """
        )
        layout.addWidget(self.preview_label, 1)

    def reset_preview(self, status_text):
        self.preview_pixmap = None
        self.status_label.setText(status_text)
        self.preview_label.clear()
        self.preview_label.setText("Preview")

    def set_status(self, status_text):
        self.status_label.setText(status_text)

    def set_preview_pixmap(self, pixmap):
        self.preview_pixmap = pixmap
        self.refresh_preview_pixmap()

    def refresh_preview_pixmap(self):
        if self.preview_pixmap is None:
            return

        scaled = self.preview_pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def close_preview_window(self):
        self._closing_programmatically = True
        self.close()
        self._closing_programmatically = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_preview_pixmap()

    def closeEvent(self, event):
        super().closeEvent(event)
        if not self._closing_programmatically:
            self.close_requested.emit()


class DetectionProgressDialog(QDialog):
    """Progress UI that stays visible until the worker thread actually exits."""

    canceled = Signal()

    def __init__(self, message, maximum, parent=None):
        super().__init__(parent)
        self._allow_close = False
        self._cancel_requested = False
        self.setWindowTitle("AI 객체 탐지 진행 중")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, maximum if maximum > 0 else 0)
        layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.request_cancel)
        layout.addWidget(self.cancel_button)

    def setValue(self, value):
        self.progress_bar.setValue(value)

    def setLabelText(self, message):
        if not self._cancel_requested:
            self.label.setText(message)

    def set_terminal_text(self, message):
        self.label.setText(message)
        self.cancel_button.setEnabled(False)

    def mark_cancelling(self, message="취소 요청됨 — 현재 처리를 마치는 중…"):
        self._cancel_requested = True
        self.label.setText(message)
        self.cancel_button.setEnabled(False)

    @Slot()
    def request_cancel(self):
        if self._cancel_requested:
            return
        self.mark_cancelling()
        self.canceled.emit()

    def finish(self):
        self._allow_close = True
        self.close()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        self.request_cancel()
        event.ignore()


class DetectionWorker(QThread):
    """
    YOLO 객체 탐지를 백그라운드에서 수행하는 워커 스레드
    """

    # 시그널 정의
    progress_signal = Signal(int, str)  # 진행률 (퍼센트/카운트, 메시지)
    log_signal = Signal(str)  # 로그 메시지
    error_signal = Signal(str)  # 에러 메시지
    finished_signal = Signal(dict)  # 작업 완료 시그널 (최종 결과 포함)
    frame_signal = Signal(object)  # GUI 미리보기용 프레임

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.is_running = True
        self.model = None

        # 파라미터 언패킹
        self.source = normalize_source_name(params.get("source"))
        self.juso = params.get("juso")
        self.datasize = params.get("datasize")
        self.imgsz = params.get("imgsz")
        self.percentage = params.get("percentage")
        self.device = params.get("device")
        self.classes_to_detect = params.get("classes_to_detect")
        self.file_count = params.get("file_count", 0)
        self.only_person = params.get("only_person", False)
        self.only_car = params.get("only_car", False)

        # 카운터 초기화
        self.total_people_detected = 0
        self.total_cars_detected = 0
        self.original_files = []
        self.output_files = []
        self.errors = []
        self.warnings = []
        self.processed_count = 0
        self.attempted_count = 0
        self.succeeded_count = 0
        self.failed_count = 0
        self.video_frame_count = 0
        self.reported_video_frame_count = None
        self.written_frame_count = 0
        self._video_output_expected_frames = None

    def run(self):
        start_time = time.time()
        detected_files = []
        output_folder = DETECTED_OUTPUT_DIR
        folder_existed = output_folder.exists()
        folder_status = "결과 폴더를 준비하지 못했습니다."
        final_status = DETECTION_STATUS_FAILED
        fatal_error = None

        try:
            self.log_signal.emit("🚀 작업 스레드 시작")

            # 모델 로드
            self.log_signal.emit(f"모델 로딩 중: {self.datasize}")
            self.model = YOLO(resolve_model_source(self.datasize))

            output_folder.mkdir(parents=True, exist_ok=True)
            folder_status = (
                "폴더(detected_files)가 이미 존재합니다."
                if folder_existed
                else "새로운 폴더(detected_files)가 생성되었습니다."
            )

            if not self.is_running:
                self.log_signal.emit("모델 로딩 후 취소 요청을 확인했습니다.")
                final_status = DETECTION_STATUS_CANCELLED

            # 소스 유형에 따른 처리
            elif self.source == "사진":
                self.process_images(output_folder, detected_files)
                final_status = self.get_image_terminal_status()
            elif is_live_video_source(self.source):
                video_result = self.process_video(output_folder)
                if video_result["had_detection"]:
                    detected_files.append(video_result["source"])
                final_status = video_result["status"]
            else:
                raise ValueError("입력 소스를 선택해 주세요.")

        except Exception as e:
            fatal_error = str(e)
            if fatal_error not in self.errors:
                self.errors.append(fatal_error)
            if not self.is_running:
                final_status = DETECTION_STATUS_CANCELLED
            elif self.source == "사진" and self.succeeded_count > 0:
                final_status = DETECTION_STATUS_PARTIAL
            else:
                final_status = DETECTION_STATUS_FAILED
            if self.is_running:
                self.error_signal.emit(fatal_error)
        finally:
            final_result = {
                "source": self.source,
                "image_count": self.file_count if self.source == "사진" else 0,
                "detected_files": detected_files,
                "original_files": list(self.original_files),
                "output_files": list(self.output_files),
                "output_folder": str(output_folder),
                "folder_status": folder_status,
                "execution_time": time.time() - start_time,
                "total_people": self.total_people_detected,
                "total_cars": self.total_cars_detected,
                "processed_count": self.processed_count,
                "attempted_count": self.attempted_count,
                "succeeded_count": self.succeeded_count,
                "failed_count": self.failed_count,
                "video_frame_count": self.video_frame_count,
                "reported_video_frame_count": self.reported_video_frame_count,
                "written_frame_count": self.written_frame_count,
                "errors": list(self.errors),
                "warnings": list(self.warnings),
                "fatal_error": fatal_error,
                "status": final_status,
                "count_mode": "max_per_frame" if self.source != "사진" else "sum_per_image",
                "only_person": self.only_person,
                "only_car": self.only_car,
                "classes_to_detect": list(self.classes_to_detect or []),
            }
            self.finished_signal.emit(final_result)

            # The model belongs to the worker, so release it in the worker lifecycle.
            self.model = None
            gc.collect()
            clear_torch_cache(self.device)

    def get_image_terminal_status(self):
        """사진 시도 결과로 종료 상태를 계산한다."""
        if not self.is_running:
            return DETECTION_STATUS_CANCELLED
        if self.succeeded_count and self.failed_count:
            return DETECTION_STATUS_PARTIAL
        if self.succeeded_count:
            return DETECTION_STATUS_COMPLETED
        return DETECTION_STATUS_FAILED

    def stop(self):
        """작업 중지 요청"""
        self.is_running = False

    def open_video_capture(self, source_path):
        """환경에 맞는 OpenCV 비디오 캡처 객체를 생성."""
        attempts = []

        if isinstance(source_path, int):
            if platform.system() == "Darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
                attempts.append((source_path, cv2.CAP_AVFOUNDATION))
            attempts.append((source_path, None))
        else:
            attempts.append((source_path, None))

        cap = None
        for current_source, backend in attempts:
            cap = (
                cv2.VideoCapture(current_source, backend)
                if backend is not None
                else cv2.VideoCapture(current_source)
            )
            if cap.isOpened():
                return cap
            cap.release()

        return cap

    def process_images(self, output_folder, detected_files):
        """이미지 파일 처리 로직"""
        if isinstance(self.juso, (str, os.PathLike)):
            sources = [str(self.juso)]
        elif isinstance(self.juso, (list, tuple)):
            sources = [str(path) for path in self.juso]
        else:
            raise ValueError("사진 파일 또는 폴더 경로를 확인해 주세요.")

        for source in sources:
            if not self.is_running:
                break

            if os.path.isdir(source):
                files_in_folder = sorted(
                    str(file)
                    for file in Path(source).iterdir()
                    if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
                )
                if not files_in_folder:
                    self.record_image_failure(
                        f"지원하는 사진이 없는 폴더: {source}"
                    )
                for file in files_in_folder:
                    if not self.is_running:
                        break

                    self.process_image_attempt(file, detected_files, output_folder)

            elif os.path.isfile(source) and Path(source).suffix.lower() in IMAGE_EXTENSIONS:
                self.process_image_attempt(source, detected_files, output_folder)
            else:
                self.record_image_failure(
                    f"지원하지 않거나 존재하지 않는 사진 경로: {source}"
                )

    def process_image_attempt(self, source, detected_files, output_folder):
        """사진 한 건의 시도·성공·실패 수를 기록한다."""
        self.attempted_count += 1
        succeeded = self.process_single_file(source, detected_files, output_folder)
        if succeeded is False:
            self.failed_count += 1
        else:
            self.succeeded_count += 1

        self.processed_count = self.attempted_count
        self.progress_signal.emit(
            self.processed_count,
            f"진행 중... {self.processed_count} / {self.file_count}",
        )
        if self.processed_count % 10 == 0:
            gc.collect()
            clear_torch_cache(self.device)

    def record_image_failure(self, error_message):
        """열 수 없는 입력 하나를 실패 시도로 기록한다."""
        self.attempted_count += 1
        self.failed_count += 1
        self.processed_count = self.attempted_count
        self.errors.append(error_message)
        self.log_signal.emit(error_message)
        self.progress_signal.emit(
            self.processed_count,
            f"진행 중... {self.processed_count} / {self.file_count}",
        )

    def process_single_file(self, source, detected_files, output_folder):
        """단일 파일 YOLO 처리"""
        try:
            results = self.model(
                source,
                stream=True,
                imgsz=self.imgsz,
                save=False,
                conf=self.percentage,
                device=self.device,
                classes=self.classes_to_detect,
            )

            source_people = 0
            source_cars = 0
            source_detected = False
            result_count = 0

            for result in results:
                result_count += 1
                try:
                    detected_classes = result.names
                    detected_ids = result.boxes.cls if result.boxes is not None else []

                    people_count = sum(
                        1 for cls_id in detected_ids if detected_classes[int(cls_id)] == "person"
                    )
                    car_count = sum(
                        1
                        for cls_id in detected_ids
                        if detected_classes[int(cls_id)] in ["car", "bus", "truck"]
                    )
                    source_people += people_count
                    source_cars += car_count

                    if (people_count > 0 or car_count > 0) and not source_detected:
                        original_path, detected_path = self.file_copy(source, result, output_folder)
                        detected_files.append(source)
                        self.original_files.append(original_path)
                        if detected_path:
                            self.output_files.append(detected_path)
                        source_detected = True
                finally:
                    del result

            if result_count == 0:
                raise RuntimeError("모델이 사진 처리 결과를 반환하지 않았습니다.")

            self.total_people_detected += source_people
            self.total_cars_detected += source_cars
            return True

        except Exception as e:
            error_message = f"파일 처리 오류 ({source}): {e}"
            self.errors.append(error_message)
            self.log_signal.emit(error_message)
            return False

    def process_video(self, output_folder):
        """비디오/캡처보드를 처리하고 최대 동시 탐지 수를 집계한다."""
        cap = None
        out = None
        should_save_video = self.source == VIDEO_FILE_SOURCE
        output_video_filename = None
        partial_video_filename = None
        had_detection = False
        frame_counter = 0
        written_frame_count = 0
        terminal_status = DETECTION_STATUS_FAILED
        reported_frame_count = None
        last_frame_position_ms = None
        source_path = None

        try:
            if self.source == VIDEO_FILE_SOURCE:
                if isinstance(self.juso, (list, tuple)):
                    if len(self.juso) != 1:
                        raise ValueError("영상은 한 번에 하나만 선택해 주세요.")
                source_path = resolve_video_source_path(self.source, self.juso)

                source_file = Path(source_path)
                if not source_file.is_file() or source_file.suffix.lower() not in VIDEO_EXTENSIONS:
                    raise ValueError("지원하는 영상 파일을 선택해 주세요.")

                output_candidate = Path(output_folder) / f"detected_{source_file.stem}.mp4"
                output_video_filename = Path(self.get_unique_filename(str(output_candidate)))
                partial_video_filename = output_video_filename.with_name(
                    f".{output_video_filename.stem}.{uuid4().hex}.partial.mp4"
                )
            else:
                source_path = resolve_video_source_path(self.source, self.juso)

            cap = self.open_video_capture(source_path)
            if not cap.isOpened():
                if isinstance(source_path, int):
                    raise Exception(
                        "카메라 또는 캡처보드를 열 수 없습니다. macOS에서는 카메라 권한을 "
                        f"허용하고 장치 번호({source_path})를 확인해 주세요."
                    )
                raise Exception("카메라 또는 영상을 열 수 없습니다.")

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            fps_is_reported = math.isfinite(fps) and fps > 0
            if should_save_video:
                raw_frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if math.isfinite(raw_frame_count) and raw_frame_count > 0:
                    reported_frame_count = int(round(raw_frame_count))
                    self.reported_video_frame_count = reported_frame_count

            if frame_width <= 0 or frame_height <= 0:
                raise ValueError("영상 해상도를 확인할 수 없습니다.")
            if not math.isfinite(fps) or fps <= 0:
                fps = 30.0

            if should_save_video:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                Path(output_folder).mkdir(parents=True, exist_ok=True)
                out = cv2.VideoWriter(
                    str(partial_video_filename),
                    fourcc,
                    fps,
                    (frame_width, frame_height),
                )
                if not out.isOpened():
                    raise RuntimeError("탐지 결과 영상을 저장할 수 없습니다.")

            fps_buffer = deque(maxlen=10)
            self.log_signal.emit("실시간 미리보기를 별도 창에 표시합니다.")

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_position_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                if math.isfinite(frame_position_ms) and frame_position_ms >= 0:
                    last_frame_position_ms = frame_position_ms

                results_list = self.model(
                    frame,
                    imgsz=self.imgsz,
                    verbose=False,
                    conf=self.percentage,
                    device=self.device,
                    classes=self.classes_to_detect,
                )

                if not results_list:
                    raise RuntimeError("모델이 영상 프레임 처리 결과를 반환하지 않았습니다.")

                result = results_list[0]
                try:
                    im_array = result.plot()

                    # 카운팅 로직
                    person_count = 0
                    car_count = 0
                    if result.boxes is not None:
                        for box in result.boxes:
                            cls_id = int(box.cls.item())
                            cls_name = result.names[cls_id]
                            if cls_name == "person":
                                person_count += 1
                            elif cls_name in ["car", "bus", "truck"]:
                                car_count += 1

                    self.total_people_detected = max(self.total_people_detected, person_count)
                    self.total_cars_detected = max(self.total_cars_detected, car_count)
                    had_detection = had_detection or person_count > 0 or car_count > 0

                    # FPS 계산
                    frame_time_ms = sum(result.speed.values())
                    if frame_time_ms > 0:
                        fps_current = 1000 / frame_time_ms
                        fps_buffer.append(fps_current)
                        avg_fps = np.mean(fps_buffer)
                        fps_text = f"FPS: {avg_fps:.2f}"
                    else:
                        fps_text = "FPS: N/A"

                    # 텍스트 그리기 (간소화)
                    self.draw_info(im_array, fps_text, person_count, car_count)

                    rgb_frame = cv2.cvtColor(im_array, cv2.COLOR_BGR2RGB)
                    height, width, channels = rgb_frame.shape
                    bytes_per_line = channels * width
                    preview_image = QImage(
                        rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
                    ).copy()
                    self.frame_signal.emit(preview_image)

                    if should_save_video and out is not None:
                        out.write(im_array)
                        written_frame_count += 1

                finally:
                    del result
                    del results_list

                frame_counter += 1
                self.processed_count = frame_counter
                if frame_counter % 100 == 0:
                    gc.collect()
                    clear_torch_cache(self.device)

            self.video_frame_count = frame_counter
            self.written_frame_count = written_frame_count

            if not self.is_running:
                terminal_status = DETECTION_STATUS_CANCELLED
            elif self.source == CAPTURE_BOARD_SOURCE:
                terminal_status = DETECTION_STATUS_DISCONNECTED
                disconnect_message = (
                    "캡처보드에서 영상 프레임을 더 이상 읽지 못했습니다. "
                    "장치 연결 상태를 확인해 주세요."
                )
                self.errors.append(disconnect_message)
                self.log_signal.emit(disconnect_message)
            elif frame_counter == 0:
                raise RuntimeError("입력 소스에서 영상 프레임을 읽을 수 없습니다.")
            else:
                frame_count_mismatch = (
                    reported_frame_count is not None
                    and frame_counter != reported_frame_count
                )
                reached_reported_end = self.video_reached_reported_end(
                    reported_frame_count,
                    fps if fps_is_reported else None,
                    last_frame_position_ms,
                )

                if frame_count_mismatch and not reached_reported_end:
                    terminal_status = DETECTION_STATUS_PARTIAL
                    uncertain_source_warning = (
                        "컨테이너가 보고한 재생 끝보다 빠르게 영상 프레임 읽기가 "
                        f"종료되었습니다: 보고 {reported_frame_count}프레임, "
                        f"실제 처리 {frame_counter}프레임. 손상된 입력일 수도 있지만 "
                        "오디오 등 다른 트랙이 더 긴 정상 컨테이너일 수도 있어, "
                        "실제로 읽고 전체 재검증한 결과를 부분 완료로 보존합니다."
                    )
                    self.warnings.append(uncertain_source_warning)
                    self.log_signal.emit(uncertain_source_warning)
                else:
                    terminal_status = DETECTION_STATUS_COMPLETED

                if frame_count_mismatch and reached_reported_end:
                    frame_count_warning = (
                        "영상 컨테이너가 보고한 프레임 수와 실제 읽은 수가 "
                        f"다릅니다: 보고 {reported_frame_count}프레임, "
                        f"실제 처리 {frame_counter}프레임. "
                        "결과는 실제로 읽은 프레임을 기준으로 검증합니다."
                    )
                    self.warnings.append(frame_count_warning)
                    self.log_signal.emit(frame_count_warning)

        finally:
            # Preserve progress even when model inference, plotting, or writing
            # raises before the normal loop-exit bookkeeping is reached.
            self.video_frame_count = frame_counter
            self.written_frame_count = written_frame_count
            if cap:
                cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            gc.collect()
            clear_torch_cache(self.device)
            if partial_video_filename is not None and terminal_status not in {
                DETECTION_STATUS_COMPLETED,
                DETECTION_STATUS_PARTIAL,
            }:
                partial_video_filename.unlink(missing_ok=True)

        committed_output = None
        if should_save_video and terminal_status in {
            DETECTION_STATUS_COMPLETED,
            DETECTION_STATUS_PARTIAL,
        }:
            self._video_output_expected_frames = written_frame_count
            try:
                output_is_valid = self.validate_video_output(partial_video_filename)
            except Exception:
                if partial_video_filename is not None:
                    partial_video_filename.unlink(missing_ok=True)
                raise
            finally:
                self._video_output_expected_frames = None

            if not self.is_running:
                terminal_status = DETECTION_STATUS_CANCELLED
                if partial_video_filename is not None:
                    partial_video_filename.unlink(missing_ok=True)
            elif written_frame_count != frame_counter or not output_is_valid:
                if partial_video_filename is not None:
                    partial_video_filename.unlink(missing_ok=True)
                raise RuntimeError("탐지 결과 영상이 정상적으로 저장되지 않았습니다.")

            if terminal_status in {
                DETECTION_STATUS_COMPLETED,
                DETECTION_STATUS_PARTIAL,
            }:
                try:
                    os.replace(partial_video_filename, output_video_filename)
                except Exception:
                    partial_video_filename.unlink(missing_ok=True)
                    raise
                committed_output = output_video_filename
                self.output_files.append(str(committed_output.resolve()))

        return {
            "source": source_path,
            "had_detection": had_detection,
            "output_file": str(committed_output) if committed_output else None,
            "frame_count": frame_counter,
            "written_frame_count": written_frame_count,
            "reported_frame_count": reported_frame_count,
            "status": terminal_status,
        }

    @staticmethod
    def video_reached_reported_end(reported_frames, fps, last_position_ms):
        """VFR frame-count mismatch가 실제 조기 종료인지 재생 시각으로 구분한다."""
        if (
            reported_frames is None
            or reported_frames <= 0
            or fps is None
            or not math.isfinite(fps)
            or fps <= 0
            or last_position_ms is None
            or not math.isfinite(last_position_ms)
            or last_position_ms < 0
        ):
            return False

        reported_duration_ms = reported_frames * 1000.0 / fps
        tolerance_ms = max(VIDEO_END_TOLERANCE_MS, 1.5 * 1000.0 / fps)
        return last_position_ms + tolerance_ms >= reported_duration_ms

    def validate_video_output(self, output_path):
        """저장된 영상의 모든 프레임을 다시 읽어 불완전 출력을 거부한다."""
        if output_path is None or not output_path.is_file() or output_path.stat().st_size <= 0:
            return False

        verification_capture = cv2.VideoCapture(str(output_path))
        try:
            if not verification_capture.isOpened():
                return False

            decoded_frame_count = 0
            while True:
                if not self.is_running:
                    return False
                ret, frame = verification_capture.read()
                if not ret:
                    break
                if frame is None or frame.size <= 0:
                    return False
                decoded_frame_count += 1

            expected_frames = self._video_output_expected_frames
            if decoded_frame_count <= 0:
                return False
            return expected_frames is None or decoded_frame_count == expected_frames
        finally:
            verification_capture.release()

    def draw_info(self, img, fps_text, person_count, car_count):
        """화면에 정보 표시"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, fps_text, (10, 30), font, 0.7, (0, 255, 0), 2)
        cv2.putText(img, f"Person: {person_count}", (10, 60), font, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Car: {car_count}", (10, 90), font, 0.7, (255, 255, 255), 2)

    def file_copy(self, source, result, output_folder):
        """Save only this inference result and atomically publish the annotated image."""
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        source_path = Path(source)
        original_destination = output_folder / ("original_" + os.path.basename(source))
        result_destination = output_folder / f"detected_{source_path.stem}.jpg"

        if original_destination.exists():
            original_destination = Path(self.get_unique_filename(str(original_destination)))
        if result_destination.exists():
            result_destination = Path(self.get_unique_filename(str(result_destination)))

        partial_result = output_folder / f".{uuid4().hex}.partial.jpg"
        copied_original = False
        try:
            result.save(filename=str(partial_result))
            if not partial_result.is_file() or partial_result.stat().st_size <= 0:
                raise RuntimeError("현재 탐지 결과 이미지를 저장하지 못했습니다.")

            shutil.copy2(source, original_destination)
            copied_original = True
            os.replace(partial_result, result_destination)
        except Exception:
            partial_result.unlink(missing_ok=True)
            if copied_original:
                original_destination.unlink(missing_ok=True)
            raise

        return (
            str(original_destination.resolve()),
            str(result_destination.resolve()),
        )

    def get_unique_filename(self, file_path):
        base, ext = os.path.splitext(file_path)
        counter = 1
        while os.path.exists(file_path):
            file_path = f"{base}_{counter}{ext}"
            counter += 1
        return file_path


class Ui_MainWindow(QMainWindow, ModernUi_MainWindow):
    def __init__(self):
        super(Ui_MainWindow, self).__init__()
        self.setupUi(self)

        # Runtime state must exist before combo/radio signals are connected.
        self.juso = None
        self.source = None
        self.datasize = None
        self.percentage = 0.1
        self.device = get_preferred_device()
        self.imgsz = 1920
        self.only_person = False
        self.only_car = False
        self.classes_to_detect = list(PERSON_AND_VEHICLE_CLASSES)
        self.total_people_detected = 0
        self.total_cars_detected = 0
        self.file_count = 0
        self.worker = None
        self.preview_window = None
        self.progress_dialog = None
        self._pending_detection_result = None
        self._pending_detection_error = None
        self._detection_output_folder = None
        self._processing = False
        self._close_requested = False
        self._close_after_worker = False
        self._closing_without_confirmation = False
        self._cleanup_done = False
        self._cancel_requested = False
        self._preview_frame_lock = threading.Lock()
        self._pending_preview_frame = None
        self._preview_accepting_frames = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(PREVIEW_REFRESH_INTERVAL_MS)
        self._preview_timer.timeout.connect(self._display_pending_preview_frame)
        self._online_notice_fetch_started = False
        self._online_notice_revision = 0
        self._online_notice_settings = QSettings(
            NOTICE_SETTINGS_ORGANIZATION, NOTICE_SETTINGS_APPLICATION
        )
        self._online_notice_loader = OnlineNoticeLoader(self)
        self._online_notice_loader.loaded.connect(self._display_online_notices)

        # 버튼 및 UI 요소 연결
        self.pushButton_close.clicked.connect(self.exit_application)
        self.pushButton_search.clicked.connect(self.browse_files)
        self.pushButton_search_2.clicked.connect(self.browse_folders)
        self.pushButton_enter.clicked.connect(self.submit)
        self.pushButton_open_output_folder.clicked.connect(self.open_detection_folder)
        self.comboBox_data.currentIndexChanged.connect(self.update_datasize)
        self.comboBox_source.currentIndexChanged.connect(self.update_source)
        self.comboBox_percentage.currentIndexChanged.connect(self.option_percentage)
        self.comboBox_device.currentIndexChanged.connect(self.option_device)
        self.comboBox_imgsz.currentIndexChanged.connect(self.option_imgsz)
        if all(
            hasattr(self, name)
            for name in ("radioButton_all", "radioButton_person", "radioButton_car")
        ):
            self.radioButton_all.toggled.connect(self.update_detection_target)
            self.radioButton_person.toggled.connect(self.update_detection_target)
            self.radioButton_car.toggled.connect(self.update_detection_target)
        else:
            # Temporary compatibility with older generated UI files.
            self.checkBox_person.stateChanged.connect(self.update_only_person)
            self.checkBox_car.stateChanged.connect(self.update_only_car)
        self.lineEdit_juso.textChanged.connect(self.update_juso)
        self.infoTabs.currentChanged.connect(self._mark_online_notices_seen)

        # 🚀 메모리 모니터링 도구 초기화
        self.memory_monitor = MemoryMonitor()
        self.memory_monitor.log_memory_usage("GUI 초기화 완료")
        self.sync_control_defaults()
        self.update_detection_target()
        self.update_action_states()
        self.set_main_status(f"준비됨 · 자동 장치: {self.device.upper()}")
        self.reset_preview("실시간 입력을 시작하면 미리보기 새창이 열립니다.")

    def showEvent(self, event):
        """Start the online-news request only after the main window is visible."""
        super().showEvent(event)
        if not self._online_notice_fetch_started:
            self._online_notice_fetch_started = True
            self._online_notice_loader.refresh()

    @staticmethod
    def run_app():
        """Create the QApplication, authenticate, and launch the main window."""
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        if start.authenticate():
            window = Ui_MainWindow()
            window.show()
            sys.exit(app.exec())

        sys.exit()

    def sync_control_defaults(self):
        """Keep visible defaults and the values sent to the worker in sync."""
        for combo, text in (
            (self.comboBox_percentage, "10%(기본값)"),
            (self.comboBox_imgsz, "1920(기본값)"),
        ):
            index = combo.findText(text)
            if index >= 0:
                combo.setCurrentIndex(index)

        self.device = get_preferred_device()
        preferred_label = {"cuda": "GPU", "mps": "MPS", "cpu": "CPU"}.get(
            self.device, "CPU"
        )
        preferred_index = self.comboBox_device.findText(preferred_label)
        if preferred_index < 0:
            preferred_index = self.comboBox_device.findText("CPU")
        if preferred_index >= 0:
            previously_blocked = self.comboBox_device.blockSignals(True)
            try:
                self.comboBox_device.setCurrentIndex(preferred_index)
            finally:
                self.comboBox_device.blockSignals(previously_blocked)

    def set_main_status(self, message):
        if hasattr(self, "status_label"):
            self.status_label.setText(message)

    @Slot(object)
    def _display_online_notices(self, result):
        """Render validated public items without interrupting the detection flow."""
        if not isinstance(result, NoticeLoadResult) or not result.items:
            self.infoTabs.setTabVisible(self.online_notice_tab_index, False)
            self.plainTextEdit_online_notice.clear()
            self._online_notice_revision = 0
            return

        sections = []
        if result.source == NOTICE_SOURCE_CACHE:
            sections.append(
                "[안내] 네트워크에서 최신 소식을 확인하지 못해 마지막으로 저장된 내용을 표시합니다."
            )
        for item in result.items:
            published_text = item.published_at.astimezone().strftime("%Y-%m-%d %H:%M")
            kind_text = NOTICE_KIND_LABELS.get(item.kind, "소식")
            heading = f"[{kind_text}] {item.title} · {published_text}"
            details = [heading, item.summary]
            if item.body != item.summary:
                details.extend(("", item.body))
            if item.version:
                details.extend(("", f"대상 버전: {item.version}"))
            if item.link_url:
                details.append(f"자세히 보기: {item.link_url}")
            sections.append("\n".join(details))

        self.plainTextEdit_online_notice.setPlainText("\n\n──────────\n\n".join(sections))
        self._online_notice_revision = result.revision
        last_seen_revision = self._last_seen_notice_revision()
        tab_title = (
            NOTICE_TAB_UNREAD_TITLE
            if result.revision > last_seen_revision
            else NOTICE_TAB_TITLE
        )
        self.infoTabs.setTabText(self.online_notice_tab_index, tab_title)
        self.infoTabs.setTabVisible(self.online_notice_tab_index, True)

    def _last_seen_notice_revision(self):
        value = self._online_notice_settings.value(NOTICE_SETTINGS_REVISION_KEY, 0)
        try:
            revision = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, revision)

    @Slot(int)
    def _mark_online_notices_seen(self, index):
        if index != self.online_notice_tab_index or not self._online_notice_revision:
            return
        last_seen_revision = self._last_seen_notice_revision()
        if self._online_notice_revision > last_seen_revision:
            self._online_notice_settings.setValue(
                NOTICE_SETTINGS_REVISION_KEY, self._online_notice_revision
            )
        self.infoTabs.setTabText(self.online_notice_tab_index, NOTICE_TAB_TITLE)

    @Slot()
    def update_detection_target(self, _checked=None):
        """Map the exclusive target radios to immutable worker parameters."""
        if hasattr(self, "radioButton_all"):
            if self.radioButton_person.isChecked():
                self.only_person, self.only_car = True, False
            elif self.radioButton_car.isChecked():
                self.only_person, self.only_car = False, True
            else:
                self.only_person, self.only_car = False, False
        self.update_detection_options()
        self.update_action_states()

    def update_detection_options(self):
        """선택된 탐지 대상에 따라 YOLO 클래스 필터를 업데이트한다."""
        if self.only_person and self.only_car:
            self.classes_to_detect = list(PERSON_AND_VEHICLE_CLASSES)
        elif self.only_person:
            self.classes_to_detect = [0]
        elif self.only_car:
            self.classes_to_detect = [2, 5, 7]
        else:
            self.classes_to_detect = list(PERSON_AND_VEHICLE_CLASSES)

    def update_only_person(self, state):
        """Compatibility handler for the former checkbox UI."""
        self.only_person = state == 2
        self.update_detection_options()
        self.update_action_states()

    def update_only_car(self, state):
        """Compatibility handler for the former checkbox UI."""
        self.only_car = state == 2
        self.update_detection_options()
        self.update_action_states()

    def input_is_ready(self):
        """Check whether the selected source currently has a usable input."""
        try:
            if self.source == "사진":
                if isinstance(self.juso, (str, os.PathLike)):
                    path = Path(self.juso).expanduser()
                    return (path.is_dir() and self.count_image_files(path) > 0) or (
                        path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
                    )
                if isinstance(self.juso, (list, tuple)):
                    return bool(self.juso) and all(
                        Path(path).is_file()
                        and Path(path).suffix.lower() in IMAGE_EXTENSIONS
                        for path in self.juso
                    )
                return False

            if self.source == VIDEO_FILE_SOURCE:
                paths = self.juso if isinstance(self.juso, (list, tuple)) else [self.juso]
                if len(paths) != 1 or not paths[0]:
                    return False
                path = Path(paths[0]).expanduser()
                return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS

            if self.source == CAPTURE_BOARD_SOURCE:
                return resolve_video_source_path(self.source, self.juso) >= 0
        except (OSError, TypeError, ValueError):
            return False
        return False

    def update_action_states(self):
        """Enable actions only when their prerequisites are satisfied."""
        controls = [
            self.comboBox_source,
            self.comboBox_data,
            self.comboBox_percentage,
            self.comboBox_device,
            self.comboBox_imgsz,
        ]
        for name in (
            "radioButton_all",
            "radioButton_person",
            "radioButton_car",
            "checkBox_person",
            "checkBox_car",
        ):
            if hasattr(self, name):
                controls.append(getattr(self, name))

        for control in controls:
            control.setEnabled(not self._processing)

        has_source = self.source in {"사진", VIDEO_FILE_SOURCE, CAPTURE_BOARD_SOURCE}
        self.lineEdit_juso.setEnabled(not self._processing and has_source)
        self.pushButton_search.setEnabled(
            not self._processing and self.source in {"사진", VIDEO_FILE_SOURCE}
        )
        self.pushButton_search_2.setEnabled(not self._processing and self.source == "사진")
        self.pushButton_enter.setEnabled(
            not self._processing and bool(self.datasize) and self.input_is_ready()
        )
        self.pushButton_open_output_folder.setEnabled(
            not self._processing and self._detection_output_folder_is_ready()
        )

    def set_processing_state(self, active):
        if active:
            self._detection_output_folder = None
        self._processing = active
        self.update_action_states()
        if active:
            self.set_main_status(f"탐지 실행 중 · {self.device.upper()}")
        else:
            self.set_main_status(f"준비됨 · 현재 장치: {self.device.upper()}")

    def _detection_output_folder_is_ready(self):
        try:
            return (
                self._detection_output_folder is not None
                and self._detection_output_folder.is_dir()
            )
        except OSError:
            return False

    def _set_detection_output_folder(self, folder):
        self._detection_output_folder = Path(folder).expanduser() if folder else None
        self.update_action_states()

    @Slot()
    def open_detection_folder(self):
        if not self._detection_output_folder_is_ready():
            self._set_detection_output_folder(None)
            QMessageBox.warning(
                self,
                "탐지 폴더 열기",
                "탐지 결과 폴더가 존재하지 않습니다. 다시 탐지를 실행해 주세요.",
            )
            return

        folder_url = QUrl.fromLocalFile(str(self._detection_output_folder.resolve()))
        if not QDesktopServices.openUrl(folder_url):
            QMessageBox.warning(
                self,
                "탐지 폴더 열기",
                "운영체제에서 탐지 결과 폴더를 열지 못했습니다.",
            )

    def exit_application(self):
        self.close()

    def closeEvent(self, event):
        if self._close_after_worker:
            event.ignore()
            return

        if not self._closing_without_confirmation and not self._close_requested:
            if not self.confirm_exit():
                event.ignore()
                return
            self._close_requested = True
        if self.worker is not None and self.worker.isRunning():
            self._close_after_worker = True
            if not self._cancel_requested:
                self._cancel_requested = True
                self.worker.stop()
            self._stop_preview_updates()
            if self.progress_dialog is not None:
                self.progress_dialog.mark_cancelling(
                    "종료 요청됨 — 현재 처리를 마친 뒤 안전하게 종료합니다…"
                )
            event.ignore()
            return

        self.cleanup_resources()
        event.accept()

    def cleanup_resources(self):
        """애플리케이션 종료 시 메모리 정리"""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        try:
            if hasattr(self, "_online_notice_loader"):
                self._online_notice_loader.cancel()

            # 🚀 메모리 사용량 최종 요약 출력
            if hasattr(self, "memory_monitor"):
                print("=" * 50)
                print("📊 메모리 사용량 최종 요약")
                print(self.memory_monitor.get_summary())
                print("=" * 50)

            # CUDA 캐시 정리
            clear_torch_cache(self.device)
            if self.device == "cuda":
                print("🧹 CUDA 메모리 캐시 정리 완료")
            elif self.device == "mps":
                print("🧹 MPS 메모리 캐시 정리 완료")

            # 가비지 컬렉션 강제 실행
            gc.collect()
            print("🧹 가비지 컬렉션 완료")

            self.close_progress_dialog()
            self.close_preview_window()

            # 🚀 최종 메모리 상태 확인
            if hasattr(self, "memory_monitor"):
                self.memory_monitor.log_memory_usage("프로그램 종료 시")

        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")

    @Slot()
    def on_worker_thread_finished(self):
        """Finalize UI only after QThread.finished confirms native thread exit."""
        self._stop_preview_updates()
        worker = self.sender()
        if worker is self.worker:
            self.worker = None
        if worker is not None:
            worker.deleteLater()

        self.close_progress_dialog()
        self.set_processing_state(False)

        if self._close_after_worker:
            self._close_after_worker = False
            self._closing_without_confirmation = True
            self.close()
            return

        pending_error = self._pending_detection_error
        pending_result = self._pending_detection_result
        self._pending_detection_error = None
        self._pending_detection_result = None

        if pending_result is not None:
            self.present_detection_result(pending_result)
        elif pending_error:
            # DetectionWorker normally emits a structured result even for fatal
            # failures. Keep this branch for alternate/test workers that only
            # provide the legacy error signal.
            self.set_main_status("탐지 중 오류가 발생했습니다")
            QMessageBox.critical(
                self, "작업 오류", f"작업 중 오류가 발생했습니다:\n{pending_error}"
            )

    def close_progress_dialog(self):
        if self.progress_dialog is not None:
            self.progress_dialog.finish()
            self.progress_dialog.deleteLater()
            self.progress_dialog = None

    def reset_preview(self, status_text):
        """미리보기 영역을 기본 상태로 되돌린다."""
        if self.preview_window is not None:
            self.preview_window.reset_preview(status_text)

    def _start_preview_updates(self):
        """Accept worker frames into a one-frame mailbox and refresh at 20 FPS."""
        with self._preview_frame_lock:
            self._pending_preview_frame = None
            self._preview_accepting_frames = True
        self._preview_timer.start()

    def _stop_preview_updates(self):
        """Stop presentation and release any frame still held by the mailbox."""
        self._preview_timer.stop()
        with self._preview_frame_lock:
            self._preview_accepting_frames = False
            self._pending_preview_frame = None

    @Slot()
    def _display_pending_preview_frame(self):
        """Present only the most recent frame received since the last timer tick."""
        with self._preview_frame_lock:
            image = self._pending_preview_frame
            self._pending_preview_frame = None

        if image is None or image.isNull():
            return

        if self.preview_window is not None and self.preview_window.isVisible():
            self.preview_window.set_status("실시간 탐지 프레임을 표시하는 중입니다.")
            self.preview_window.set_preview_pixmap(QPixmap.fromImage(image))

    def ensure_preview_window(self):
        """별도 미리보기 창을 준비한다."""
        if self.preview_window is None:
            self.preview_window = PreviewWindow()
            self.preview_window.close_requested.connect(self.handle_preview_window_closed)
        return self.preview_window

    def show_preview_window(self, status_text):
        """별도 미리보기 창을 열고 상태를 표시한다."""
        preview_window = self.ensure_preview_window()
        preview_window.reset_preview(status_text)
        preview_window.show()
        preview_window.raise_()
        preview_window.activateWindow()
        self._start_preview_updates()

    def close_preview_window(self):
        """별도 미리보기 창을 닫는다."""
        self._stop_preview_updates()
        if self.preview_window is not None and self.preview_window.isVisible():
            self.preview_window.close_preview_window()

    @Slot(object)
    def update_preview_frame(self, image):
        """Keep only the latest worker frame without touching GUI objects."""
        if image is None or image.isNull():
            return

        with self._preview_frame_lock:
            if self._preview_accepting_frames:
                self._pending_preview_frame = image

    @Slot()
    def handle_preview_window_closed(self):
        """미리보기 창을 닫으면 실시간 탐지도 함께 중지한다."""
        self._stop_preview_updates()
        self.cancel_detection()

    @Slot()
    def cancel_detection(self):
        """Request cooperative cancellation without reporting immediate completion."""
        if (
            not self._cancel_requested
            and self.worker is not None
            and self.worker.isRunning()
        ):
            self._cancel_requested = True
            self._stop_preview_updates()
            self.worker.stop()
            if self.progress_dialog is not None:
                self.progress_dialog.mark_cancelling()
            self.set_main_status("취소 요청됨 · 현재 처리를 마치는 중")

    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "종료 확인",
            "정말로 종료하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def update_source(self, index):
        selection = self.comboBox_source.itemText(index)
        if selection == "선택하세요":
            self.source = None
            self.file_count = 0
            self.lineEdit_juso.clear()
            self.juso = None
            self.label_5.setText("3. 파일 또는 폴더")
            self.lineEdit_juso.setPlaceholderText("탐지할 파일 또는 폴더 경로를 선택하세요")
            self.close_preview_window()
            self.update_action_states()
            self.set_main_status("입력 소스와 모델을 선택해 주세요")
            return
        else:
            self.source = normalize_source_name(selection)
            self.file_count = 0
            self.lineEdit_juso.clear()
            self.juso = None

        if self.source == CAPTURE_BOARD_SOURCE:
            self.label_5.setText("3. 장치 번호")
            self.lineEdit_juso.setPlaceholderText(
                "캡처 장치 번호를 입력하세요. 비우면 0번 장치를 사용합니다."
            )
            self.reset_preview(
                "캡처 장치 번호를 입력한 뒤 탐지 시작을 누르면 미리보기 새창이 열립니다."
            )
        elif self.source == VIDEO_FILE_SOURCE:
            self.label_5.setText("3. 영상 파일")
            self.lineEdit_juso.setPlaceholderText("탐지할 영상 파일 하나를 선택하세요")
            self.reset_preview("영상 파일 탐지를 시작하면 미리보기 새창이 열립니다.")
        else:
            self.label_5.setText("3. 파일 또는 폴더")
            self.lineEdit_juso.setPlaceholderText("탐지할 파일 또는 폴더 경로를 선택하세요")
            self.reset_preview("실시간 입력을 시작하면 미리보기 새창이 열립니다.")
            self.close_preview_window()
        self.update_action_states()
        self.set_main_status("입력 경로와 탐지 모델을 확인해 주세요")

    def update_datasize(self, index):
        selection = self.comboBox_data.itemText(index)
        if selection == "선택하세요":
            self.datasize = None
            self.update_action_states()
            return
        else:
            size_dict = {
                "YoloV26_최대(추천)": "yolo26x.pt",
                "YoloV26_대": "yolo26l.pt",
                "YoloV26_중": "yolo26m.pt",
                "YoloV26_소": "yolo26s.pt",
                "YoloV26_최소": "yolo26n.pt",
                "YoloV11_최대": "yolo11x.pt",
                "YoloV11_대": "yolo11l.pt",
                "YoloV11_중": "yolo11m.pt",
                "YoloV11_소": "yolo11s.pt",
                "YoloV11_최소": "yolo11n.pt",
                "YoloV12(최대)": "yolo12x.pt",
                "YoloV12(최소)": "yolo12n.pt",
                "화염전용탐지(예정)": None,
            }
            self.datasize = size_dict[selection]
        self.update_action_states()

    def option_imgsz(self, index):
        selection = self.comboBox_imgsz.itemText(index)
        if selection == "해상도":
            self.imgsz = 1920
        else:
            size_dict = {
                "640": 640,
                "1080": 1080,
                "1280": 1280,
                "1680": 1680,
                "1920(기본값)": 1920,
                "3000": 3000,
                "4000(*)": 4000,
            }
            self.imgsz = size_dict[selection]
        self.update_action_states()

    def option_percentage(self, index):
        selection = self.comboBox_percentage.itemText(index)
        if selection == "신뢰도":
            self.percentage = 0.1
        else:
            size_dict = {
                "5%": 0.05,
                "10%(기본값)": 0.1,
                "15%": 0.15,
                "20%": 0.2,
                "30%": 0.3,
                "50%": 0.5,
                "80%": 0.8,
            }
            self.percentage = size_dict[selection]
        self.update_action_states()

    def option_device(self, index):
        """사용할 추론 장치를 선택."""
        selection = self.comboBox_device.itemText(index)
        device_options = {"CPU": "cpu", "GPU": "cuda", "MPS": "mps"}
        selected_device = device_options.get(selection, get_preferred_device())

        if selected_device == "cuda" and not torch.cuda.is_available():
            QMessageBox.warning(self, "GPU 사용 불가", "GPU를 사용할 수 없어 CPU로 전환합니다.")
            selected_device = "cpu"
        elif selected_device == "mps" and not is_mps_available():
            QMessageBox.warning(self, "MPS 사용 불가", "MPS를 사용할 수 없어 CPU로 전환합니다.")
            selected_device = "cpu"

        self.device = selected_device
        automatic = selection in {"자동", "사용장치"}
        prefix = "자동 감지 장치" if automatic else "선택 장치"
        self.set_main_status(f"{prefix}: {self.device.upper()}")
        self.update_action_states()

    def update_juso(self, text):
        """사용자가 lineEdit_juso에 입력한 텍스트를 저장하는 함수"""
        normalized_text = text.strip()

        if normalize_source_name(self.source) == CAPTURE_BOARD_SOURCE:
            self.juso = normalized_text if normalized_text else None
        else:
            self.juso = text if normalized_text else None
        self.update_action_states()

    def browse_files(self):
        if self.source not in {"사진", VIDEO_FILE_SOURCE}:
            QMessageBox.warning(self, "입력 확인", "먼저 사진 또는 영상 입력 소스를 선택해 주세요.")
            return

        if self.source == VIDEO_FILE_SOURCE:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "영상 파일 선택",
                "",
                "영상 파일 (*.mp4 *.mov *.avi *.mkv *.wmv *.webm)",
            )
            file_paths = [file_path] if file_path else []
        else:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "사진 파일 선택",
                "",
                "사진 파일 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)",
            )

        if file_paths:
            self.lineEdit_juso.setText(", ".join(file_paths))
            self.juso = file_paths
            self.file_count = len(self.juso)
            if len(self.juso) == 1:
                print(self.juso)
            else:
                print(f"선택한 이미지 파일 수: {len(self.juso)}개")
            self.update_action_states()

    def browse_folders(self):
        if self.source != "사진":
            QMessageBox.information(self, "입력 안내", "사진 입력을 선택한 경우에만 폴더를 고를 수 있습니다.")
            return

        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder_path:
            folder_path = Path(folder_path).as_posix()  # 슬래시(/)로 경로 변경
            folder_path += "/"  # 마지막 슬래시 추가
            self.lineEdit_juso.setText(folder_path)
            self.juso = Path(folder_path)
            self.file_count = self.count_image_files(folder_path)
            print("선택한 폴더 경로:", self.juso)
            # 이미지 파일 개수 확인

            print(f"선택한 폴더에 있는 이미지 파일 수: {self.file_count}개")
            self.update_action_states()
        else:
            print("폴더가 선택되지 않았습니다.")

    def count_image_files(self, folder_path):
        """폴더 안의 이미지 파일 개수를 반환합니다."""
        folder = Path(folder_path)

        if folder.is_dir():
            # 폴더 안에서 이미지 파일 개수를 확인
            image_files = [
                file
                for file in folder.glob("*")
                if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
            ]
            return len(image_files)
        else:
            return 0

    def submit(self):
        """실행 버튼 클릭 시 호출 - 스레드 시작"""
        # 중복 실행 방지
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "작업 안내", "이미 작업이 진행 중입니다.")
            return

        if self.source not in ["사진", VIDEO_FILE_SOURCE, CAPTURE_BOARD_SOURCE]:
            QMessageBox.warning(self, "입력 확인", "입력 소스를 선택해 주세요.")
            return

        if not self.datasize:
            selected_model = self.comboBox_data.currentText()
            message = (
                "화염 전용 탐지는 아직 구현되지 않았습니다. 다른 모델을 선택해 주세요."
                if "화염" in selected_model
                else "탐지 모델을 선택해 주세요."
            )
            QMessageBox.warning(self, "입력 확인", message)
            return

        if self.source == "사진":
            if not self.juso:
                QMessageBox.warning(self, "입력 확인", "사진 파일 또는 폴더를 선택해 주세요.")
                return

            if isinstance(self.juso, (str, os.PathLike)):
                path = Path(self.juso).expanduser()
                if not path.exists():
                    QMessageBox.warning(self, "입력 확인", "사진 경로가 존재하지 않습니다.")
                    return
                if path.is_dir():
                    self.juso = path.resolve()
                    self.file_count = self.count_image_files(path)
                    if self.file_count == 0:
                        QMessageBox.warning(
                            self, "입력 확인", "선택한 폴더에 지원하는 사진이 없습니다."
                        )
                        return
                elif path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.juso = [str(path.resolve())]
                    self.file_count = 1
                else:
                    QMessageBox.warning(self, "입력 확인", "지원하는 사진 파일을 선택해 주세요.")
                    return
            elif isinstance(self.juso, (list, tuple)):
                image_paths = [Path(path).expanduser() for path in self.juso]
                if not image_paths or any(
                    not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS
                    for path in image_paths
                ):
                    QMessageBox.warning(self, "입력 확인", "선택한 사진 파일을 확인해 주세요.")
                    return
                self.juso = [str(path.resolve()) for path in image_paths]
                self.file_count = len(self.juso)
            else:
                QMessageBox.warning(self, "입력 확인", "사진 경로 형식을 확인해 주세요.")
                return

        elif self.source == VIDEO_FILE_SOURCE:
            if isinstance(self.juso, (list, tuple)):
                if len(self.juso) != 1:
                    QMessageBox.warning(self, "입력 확인", "영상은 한 번에 하나만 선택해 주세요.")
                    return
                video_path = Path(self.juso[0]).expanduser()
            elif isinstance(self.juso, (str, os.PathLike)) and str(self.juso).strip():
                video_path = Path(self.juso).expanduser()
            else:
                QMessageBox.warning(self, "입력 확인", "영상 파일을 선택해 주세요.")
                return

            if not video_path.is_file() or video_path.suffix.lower() not in VIDEO_EXTENSIONS:
                QMessageBox.warning(self, "입력 확인", "지원하는 영상 파일을 선택해 주세요.")
                return
            self.juso = [str(video_path.resolve())]
            self.file_count = 1

        else:
            try:
                capture_device = resolve_video_source_path(self.source, self.juso)
                if capture_device < 0:
                    raise ValueError("캡처 장치 번호는 0 이상의 정수여야 합니다.")
            except ValueError as exc:
                QMessageBox.warning(self, "입력 확인", str(exc))
                return
            self.juso = capture_device

        # 파라미터 패키징
        params = {
            "source": self.source,
            "juso": self.juso,
            "datasize": self.datasize,
            "imgsz": self.imgsz,
            "percentage": self.percentage,
            "device": self.device,
            "classes_to_detect": self.classes_to_detect,
            "file_count": getattr(self, "file_count", 0),
            "only_person": self.only_person,
            "only_car": self.only_car,
        }

        # 워커 스레드 생성 및 연결
        self._pending_detection_result = None
        self._pending_detection_error = None
        self._cancel_requested = False
        self.worker = DetectionWorker(params)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.error_signal.connect(self.handle_error)
        self.worker.finished_signal.connect(self.on_detection_finished)
        self.worker.log_signal.connect(self.log_message)
        self.worker.frame_signal.connect(
            self.update_preview_frame,
            Qt.ConnectionType.DirectConnection,
        )
        self.worker.finished.connect(self.on_worker_thread_finished)

        # 진행률 다이얼로그 설정
        if self.source == "사진":
            self.progress_dialog = DetectionProgressDialog(
                "AI 객체 탐지를 준비하는 중입니다...", params["file_count"], self
            )
        elif is_live_video_source(self.source):
            self.progress_dialog = DetectionProgressDialog("실시간 탐지 실행 중입니다...", 0, self)
            self.reset_preview("실시간 영상 입력을 연결하는 중입니다.")
            self.show_preview_window("실시간 영상 입력을 연결하는 중입니다.")

        self.progress_dialog.canceled.connect(self.cancel_detection)
        self.progress_dialog.show()
        self.set_processing_state(True)

        # 스레드 시작
        try:
            self.worker.start()
        except Exception as exc:
            self.close_progress_dialog()
            self.close_preview_window()
            self.set_processing_state(False)
            self.worker.deleteLater()
            self.worker = None
            QMessageBox.critical(self, "작업 오류", f"작업 스레드를 시작하지 못했습니다:\n{exc}")
            return

        # 메모리 모니터링
        self.memory_monitor.log_memory_usage("작업 스레드 시작됨")

    @Slot(int, str)
    def update_progress(self, value, message):
        """진행률 업데이트"""
        if self.progress_dialog is not None:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    @Slot(str)
    def handle_error(self, error_msg):
        """Remember the error; native QThread.finished performs final UI cleanup."""
        self._pending_detection_error = error_msg
        if self.preview_window is not None:
            self.preview_window.set_status("실시간 탐지 중 오류가 발생했습니다.")
        if self.progress_dialog is not None:
            self.progress_dialog.set_terminal_text("오류 발생 — 작업 스레드를 정리하는 중…")
        self.close_preview_window()

    @Slot(str)
    def log_message(self, msg):
        """로그 메시지 처리"""
        print(f"[Worker] {msg}")

    @Slot(dict)
    def on_detection_finished(self, result):
        """Store the terminal result until the underlying QThread exits."""
        self._pending_detection_result = result
        status = result.get("status", DETECTION_STATUS_COMPLETED)
        output_folder = (
            result.get("output_folder") if status in RESULT_FOLDER_STATUSES else None
        )
        self._set_detection_output_folder(output_folder)
        if is_live_video_source(result["source"]):
            if self.preview_window is not None:
                preview_messages = {
                    DETECTION_STATUS_COMPLETED: "실시간 탐지가 정상 종료되었습니다.",
                    DETECTION_STATUS_CANCELLED: "실시간 탐지가 취소되었습니다.",
                    DETECTION_STATUS_DISCONNECTED: "외부 영상 입력 연결이 끊겼습니다.",
                    DETECTION_STATUS_PARTIAL: "실시간 탐지가 부분 완료되었습니다.",
                    DETECTION_STATUS_FAILED: "실시간 탐지가 실패했습니다.",
                }
                self.preview_window.set_status(
                    preview_messages.get(status, "실시간 탐지가 종료되었습니다.")
                )
        if self.progress_dialog is not None:
            if status == DETECTION_STATUS_CANCELLED:
                self.progress_dialog.mark_cancelling()
            else:
                terminal_messages = {
                    DETECTION_STATUS_COMPLETED: "탐지 완료 — 작업 스레드를 정리하는 중…",
                    DETECTION_STATUS_PARTIAL: "일부 항목 처리 완료 — 작업 스레드를 정리하는 중…",
                    DETECTION_STATUS_FAILED: "탐지 실패 — 작업 스레드를 정리하는 중…",
                    DETECTION_STATUS_DISCONNECTED: "외부 영상 연결 끊김 — 작업 스레드를 정리하는 중…",
                }
                self.progress_dialog.set_terminal_text(
                    terminal_messages.get(status, "탐지 종료 — 작업 스레드를 정리하는 중…")
                )

    def present_detection_result(self, result):
        """Present a result after native thread completion and resource release."""
        status = result.get("status", DETECTION_STATUS_COMPLETED)
        if status == DETECTION_STATUS_CANCELLED:
            self.set_main_status("탐지 작업이 취소되었습니다")
            QMessageBox.information(
                self,
                "AI 객체 탐지 취소",
                (
                    "작업이 취소되었습니다.\n\n"
                    f"취소 전 처리량: {result.get('processed_count', 0)}\n"
                    f"정상 보존된 결과 파일: {len(result.get('output_files', []))}개"
                ),
            )
            return

        status_messages = {
            DETECTION_STATUS_COMPLETED: "탐지 작업이 완료되었습니다",
            DETECTION_STATUS_PARTIAL: "탐지 작업이 부분 완료되었습니다",
            DETECTION_STATUS_FAILED: "탐지 작업이 실패했습니다",
            DETECTION_STATUS_DISCONNECTED: "외부 영상 입력 연결이 끊겼습니다",
        }
        self.set_main_status(status_messages.get(status, "탐지 작업이 종료되었습니다"))
        self.display_results_new(result)

        original_files = result.get("original_files", [])
        if (
            status in {DETECTION_STATUS_COMPLETED, DETECTION_STATUS_PARTIAL}
            and result["source"] == "사진"
            and original_files
        ):
            reply = QMessageBox.question(
                self,
                "GPS 정보 분석",
                (
                    f"{gps2.MAP_PRIVACY_NOTICE}\n\n"
                    "이번 작업에서 탐지된 사진의 GPS 정보로 "
                    "지도를 생성하시겠습니까?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                gps2.process_image_paths(
                    original_files,
                    output_directory=result.get("output_folder"),
                )

        self.memory_monitor.log_memory_usage(f"작업 종료({status})")

    def display_results_new(self, result):
        """Show a source-aware summary for a terminal detection result."""
        source = result["source"]
        status = result.get("status", DETECTION_STATUS_COMPLETED)
        image_count = result["image_count"]
        detected_files = result["detected_files"]
        folder_status = result["folder_status"]
        execution_time = result["execution_time"]
        total_people = result["total_people"]
        total_cars = result["total_cars"]
        output_files = result.get("output_files", [])
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        only_person = result.get("only_person", False)
        only_car = result.get("only_car", False)

        if is_live_video_source(source):
            status_label = {
                DETECTION_STATUS_COMPLETED: "정상 완료",
                DETECTION_STATUS_PARTIAL: "부분 완료",
                DETECTION_STATUS_FAILED: "실패",
                DETECTION_STATUS_DISCONNECTED: "입력 연결 끊김",
            }.get(status, "종료")
            frame_count = result.get("video_frame_count", result.get("processed_count", 0))
            reported_frames = result.get("reported_video_frame_count")
            message = (
                f"{folder_status}\n\n"
                f"영상 탐지 상태: {status_label}\n"
                f"처리 프레임: {frame_count}개"
            )
            if reported_frames is not None:
                message += f" / 컨테이너 보고 {reported_frames}개"
            message += f"\n실행 시간: {execution_time:.2f}초"
            if only_person and not only_car:
                message += f"\n\n최대 동시 사람 탐지 수: {total_people}명"
            elif only_car and not only_person:
                message += f"\n\n최대 동시 차량 탐지 수: {total_cars}대"
            else:
                message += f"\n\n최대 동시 탐지 수: 사람 {total_people}명, 차량 {total_cars}대"

            if output_files:
                message += f"\n결과 영상: {output_files[0]}"
        else:
            attempted_count = result.get("attempted_count", result.get("processed_count", 0))
            succeeded_count = result.get("succeeded_count", attempted_count)
            failed_count = result.get("failed_count", len(errors))
            message = (
                f"{folder_status}\n\n"
                f"선택 사진: {image_count}장\n"
                f"처리 시도: {attempted_count}장\n"
                f"처리 성공: {succeeded_count}장\n"
                f"처리 실패: {failed_count}장\n"
                f"객체 탐지: {len(detected_files)}장\n"
                f"실행 시간: {execution_time:.2f}초"
            )

            if detected_files:
                if only_person and not only_car:
                    message += f"\n\n사진 전체 누적 사람 탐지 수: {total_people}명"
                elif only_car and not only_person:
                    message += f"\n\n사진 전체 누적 차량 탐지 수: {total_cars}대"
                else:
                    message += (
                        f"\n\n사진 전체 누적 탐지 수: 사람 {total_people}명, 차량 {total_cars}대"
                    )

                message += f"\n탐지 결과 폴더: {result.get('output_folder', DETECTED_OUTPUT_DIR)}"
            elif succeeded_count == 0:
                message += "\n\n성공적으로 분석된 사진이 없습니다."
            else:
                message += "\n\n성공 처리된 사진에서는 탐지된 사람 또는 차량이 없습니다."

        if errors:
            message += f"\n\n처리하지 못한 항목: {len(errors)}개"
            for error in errors[:3]:
                message += f"\n- {error}"
            if len(errors) > 3:
                message += f"\n- 외 {len(errors) - 3}개"

        if warnings:
            message += f"\n\n주의 사항: {len(warnings)}개"
            for warning in warnings[:3]:
                message += f"\n- {warning}"

        if status == DETECTION_STATUS_FAILED:
            QMessageBox.critical(self, "AI 객체 탐지 실패", message)
        elif status in {DETECTION_STATUS_PARTIAL, DETECTION_STATUS_DISCONNECTED}:
            title = (
                "AI 객체 탐지 부분 완료"
                if status == DETECTION_STATUS_PARTIAL
                else "외부 영상 입력 연결 끊김"
            )
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, "AI 객체 탐지 완료", message)


if __name__ == "__main__":
    Ui_MainWindow.run_app()
