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
import time
from collections import deque  # 메모리 효율적인 FPS 버퍼용
from pathlib import Path

import cv2  # OpenCV 추가
import numpy as np  # Numpy 추가
import torch
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
)
from ultralytics import YOLO

from mypackage import gps2, start
from mypackage.modern_gui_fixed import ModernUi_MainWindow
from mypackage.video_source import (
    CAPTURE_BOARD_SOURCE,
    VIDEO_FILE_SOURCE,
    is_live_video_source,
    normalize_source_name,
    resolve_video_source_path,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DETECTED_OUTPUT_DIR = PROJECT_ROOT / "detected_files"
YOLO_RUNS_DIR = PROJECT_ROOT / "runs" / "detect"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"}
PERSON_AND_VEHICLE_CLASSES = [0, 2, 5, 7]


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


def is_mps_available():
    """PyTorch MPS 백엔드 사용 가능 여부."""
    return bool(
        hasattr(torch, "backends")
        and hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    )


def get_preferred_device():
    """사용 가능한 가속 장치를 우선순위대로 선택."""
    if torch.cuda.is_available():
        return "cuda"
    if is_mps_available():
        return "mps"
    return "cpu"


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


class DetectionWorker(QThread):
    """
    YOLO 객체 탐지를 백그라운드에서 수행하는 워커 스레드
    """

    # 시그널 정의
    progress_signal = Signal(int, str)  # 진행률 (퍼센트/카운트, 메시지)
    result_signal = Signal(dict)  # 탐지 결과 데이터
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
        self.processed_count = 0

    def run(self):
        start_time = time.time()
        detected_files = []
        output_folder = DETECTED_OUTPUT_DIR
        folder_existed = output_folder.exists()

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

            # 소스 유형에 따른 처리
            elif self.source == "사진":
                self.process_images(output_folder, detected_files)
            elif is_live_video_source(self.source):
                video_result = self.process_video(output_folder)
                if video_result["had_detection"]:
                    detected_files.append(video_result["source"])
            else:
                raise ValueError("입력 소스를 선택해 주세요.")

            # 최종 결과 정리
            execution_time = time.time() - start_time

            final_result = {
                "source": self.source,
                "image_count": self.file_count if self.source == "사진" else 0,
                "detected_files": detected_files,
                "original_files": list(self.original_files),
                "output_files": list(self.output_files),
                "output_folder": str(output_folder),
                "folder_status": folder_status,
                "execution_time": execution_time,
                "total_people": self.total_people_detected,
                "total_cars": self.total_cars_detected,
                "processed_count": self.processed_count,
                "errors": list(self.errors),
                "status": "completed" if self.is_running else "cancelled",
                "count_mode": "max_per_frame" if self.source != "사진" else "sum_per_image",
            }

            self.finished_signal.emit(final_result)

        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            # The model belongs to the worker, so release it in the worker lifecycle.
            self.model = None
            gc.collect()
            clear_torch_cache(self.device)

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
                for file in files_in_folder:
                    if not self.is_running:
                        break

                    self.process_single_file(file, detected_files, output_folder)
                    self.processed_count += 1
                    self.progress_signal.emit(
                        self.processed_count,
                        f"진행 중... {self.processed_count} / {self.file_count}",
                    )
                    if self.processed_count % 10 == 0:
                        gc.collect()
                        clear_torch_cache(self.device)

            elif os.path.isfile(source) and Path(source).suffix.lower() in IMAGE_EXTENSIONS:
                self.process_single_file(source, detected_files, output_folder)
                self.processed_count += 1
                self.progress_signal.emit(
                    self.processed_count,
                    f"진행 중... {self.processed_count} / {self.file_count}",
                )
                if self.processed_count % 10 == 0:
                    gc.collect()
                    clear_torch_cache(self.device)
            else:
                error_message = f"지원하지 않거나 존재하지 않는 사진 경로: {source}"
                self.errors.append(error_message)
                self.log_signal.emit(error_message)

    def process_single_file(self, source, detected_files, output_folder):
        """단일 파일 YOLO 처리"""
        try:
            results = self.model(
                source,
                stream=True,
                imgsz=self.imgsz,
                save=True,
                conf=self.percentage,
                device=self.device,
                classes=self.classes_to_detect,
                project=str(YOLO_RUNS_DIR),
                name="predict",
                exist_ok=True,
            )

            source_people = 0
            source_cars = 0
            source_detected = False

            for result in results:
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

            self.total_people_detected += source_people
            self.total_cars_detected += source_cars

        except Exception as e:
            error_message = f"파일 처리 오류 ({source}): {e}"
            self.errors.append(error_message)
            self.log_signal.emit(error_message)

    def process_video(self, output_folder):
        """비디오/캡처보드를 처리하고 최대 동시 탐지 수를 집계한다."""
        cap = None
        out = None
        should_save_video = self.source == VIDEO_FILE_SOURCE
        output_video_filename = None
        had_detection = False
        frame_counter = 0

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

            if frame_width <= 0 or frame_height <= 0:
                raise ValueError("영상 해상도를 확인할 수 없습니다.")
            if not math.isfinite(fps) or fps <= 0:
                fps = 30.0

            if should_save_video:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                Path(output_folder).mkdir(parents=True, exist_ok=True)
                out = cv2.VideoWriter(
                    str(output_video_filename),
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

                results_list = self.model(
                    frame,
                    imgsz=self.imgsz,
                    verbose=False,
                    conf=self.percentage,
                    device=self.device,
                    classes=self.classes_to_detect,
                )

                if len(results_list) > 0:
                    result = results_list[0]
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

                    # 메모리 정리
                    del result
                    del results_list

                frame_counter += 1
                self.processed_count = frame_counter
                if frame_counter % 100 == 0:
                    gc.collect()
                    clear_torch_cache(self.device)

            if frame_counter == 0 and self.is_running:
                raise RuntimeError("입력 소스에서 영상 프레임을 읽을 수 없습니다.")

        finally:
            if cap:
                cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            gc.collect()
            clear_torch_cache(self.device)

        if output_video_filename is not None and output_video_filename.exists():
            self.output_files.append(str(output_video_filename.resolve()))

        return {
            "source": source_path,
            "had_detection": had_detection,
            "output_file": str(output_video_filename) if output_video_filename else None,
            "frame_count": frame_counter,
        }

    def draw_info(self, img, fps_text, person_count, car_count):
        """화면에 정보 표시"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, fps_text, (10, 30), font, 0.7, (0, 255, 0), 2)
        cv2.putText(img, f"Person: {person_count}", (10, 60), font, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Car: {car_count}", (10, 90), font, 0.7, (255, 255, 255), 2)

    def file_copy(self, source, result, output_folder):
        """파일 복사 헬퍼"""
        output_folder = Path(output_folder)
        original_destination = output_folder / ("original_" + os.path.basename(source))
        result_dir = Path(result.save_dir)
        result_file = result_dir / os.path.basename(source)

        if original_destination.exists():
            original_destination = Path(self.get_unique_filename(str(original_destination)))

        if not result_file.exists():
            matching_results = sorted(result_dir.glob(f"{Path(source).stem}.*"))
            result_file = matching_results[0] if matching_results else result_file

        if not result_file.exists():
            raise FileNotFoundError(f"YOLO 결과 파일을 찾을 수 없습니다: {result_file}")

        shutil.copy2(source, original_destination)

        result_destination = output_folder / ("detected_" + result_file.name)
        if result_destination.exists():
            result_destination = Path(self.get_unique_filename(str(result_destination)))
        shutil.copy2(result_file, result_destination)

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

        # 버튼 및 UI 요소 연결
        self.pushButton_close.clicked.connect(self.exit_application)
        self.pushButton_search.clicked.connect(self.browse_files)
        self.pushButton_search_2.clicked.connect(self.browse_folders)
        self.pushButton_enter.clicked.connect(self.submit)
        self.comboBox_data.currentIndexChanged.connect(self.update_datasize)
        self.comboBox_source.currentIndexChanged.connect(self.update_source)
        self.comboBox_percentage.currentIndexChanged.connect(self.option_percentage)
        self.comboBox_device.currentIndexChanged.connect(self.option_device)
        self.comboBox_imgsz.currentIndexChanged.connect(self.option_imgsz)
        self.checkBox_person.stateChanged.connect(self.update_only_person)
        self.checkBox_car.stateChanged.connect(self.update_only_car)
        self.lineEdit_juso.textChanged.connect(self.update_juso)

        # 초기화
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
        self._close_requested = False
        self._close_after_worker = False
        self._closing_without_confirmation = False
        self._cleanup_done = False

        # 🚀 메모리 모니터링 도구 초기화
        self.memory_monitor = MemoryMonitor()
        self.memory_monitor.log_memory_usage("GUI 초기화 완료")
        self.reset_preview("실시간 입력을 시작하면 미리보기 새창이 열립니다.")

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

    def update_detection_options(self):
        """체크박스 상태에 따라 탐지 옵션을 업데이트"""
        if self.only_person and self.only_car:
            self.classes_to_detect = [0, 2, 5, 7]  # 사람과 자동차 탐지(자동차, 버스, 트럭)
            print("사람과 차량 탐지를 사용합니다.")
        elif self.only_person:
            self.classes_to_detect = [0]  # 사람만 탐지
            print("사람만 탐지합니다.")
        elif self.only_car:
            self.classes_to_detect = [2, 5, 7]  # 자동차만 탐지(자동차, 버스, 트럭)
            print("차량만 탐지합니다.")
        else:
            self.classes_to_detect = list(PERSON_AND_VEHICLE_CLASSES)
            print("사람과 차량 탐지를 사용합니다.")

    def update_only_person(self, state):
        """체크박스 상태 변경"""
        self.only_person = state == 2  # 체크되면 True, 아니면 False
        self.update_detection_options()

    def update_only_car(self, state):
        """체크박스 상태 변경"""
        self.only_car = state == 2  # 체크되면 True, 아니면 False
        self.update_detection_options()

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
            self.worker.stop()
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.setLabelText("현재 추론을 마친 뒤 안전하게 종료합니다...")
                self.progress_dialog.setCancelButton(None)
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

            self.close_preview_window()

            # 🚀 최종 메모리 상태 확인
            if hasattr(self, "memory_monitor"):
                self.memory_monitor.log_memory_usage("프로그램 종료 시")

        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")

    @Slot()
    def on_worker_thread_finished(self):
        """Release the completed QThread and finish a deferred app close."""
        worker = self.sender()
        if worker is self.worker:
            self.worker = None
        if worker is not None:
            worker.deleteLater()

        if self._close_after_worker:
            self._close_after_worker = False
            self._closing_without_confirmation = True
            self.close()

    def reset_preview(self, status_text):
        """미리보기 영역을 기본 상태로 되돌린다."""
        if self.preview_window is not None:
            self.preview_window.reset_preview(status_text)

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

    def close_preview_window(self):
        """별도 미리보기 창을 닫는다."""
        if self.preview_window is not None and self.preview_window.isVisible():
            self.preview_window.close_preview_window()

    @Slot(object)
    def update_preview_frame(self, image):
        """워커 스레드에서 전달한 프레임을 GUI에 표시한다."""
        if image is None or image.isNull():
            return

        if self.preview_window is not None:
            self.preview_window.set_status("실시간 탐지 프레임을 표시하는 중입니다.")
            self.preview_window.set_preview_pixmap(QPixmap.fromImage(image))

    @Slot()
    def handle_preview_window_closed(self):
        """미리보기 창을 닫으면 실시간 탐지도 함께 중지한다."""
        self.cancel_detection()
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

    @Slot()
    def cancel_detection(self):
        """Request cooperative cancellation without reporting immediate completion."""
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if hasattr(self, "progress_dialog"):
                self.progress_dialog.setLabelText("현재 추론을 마친 뒤 작업을 취소합니다...")
                self.progress_dialog.setCancelButton(None)

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
            self.pushButton_search.setEnabled(True)
            self.pushButton_search_2.setEnabled(True)
            self.close_preview_window()
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
            self.pushButton_search.setEnabled(False)
            self.pushButton_search_2.setEnabled(False)
            self.reset_preview(
                "캡처 장치 번호를 입력한 뒤 탐지 시작을 누르면 미리보기 새창이 열립니다."
            )
        elif self.source == VIDEO_FILE_SOURCE:
            self.label_5.setText("3. 영상 파일")
            self.lineEdit_juso.setPlaceholderText("탐지할 영상 파일 하나를 선택하세요")
            self.pushButton_search.setEnabled(True)
            self.pushButton_search_2.setEnabled(False)
            self.reset_preview("영상 파일 탐지를 시작하면 미리보기 새창이 열립니다.")
        else:
            self.label_5.setText("3. 파일 또는 폴더")
            self.lineEdit_juso.setPlaceholderText("탐지할 파일 또는 폴더 경로를 선택하세요")
            self.pushButton_search.setEnabled(True)
            self.pushButton_search_2.setEnabled(True)
            self.reset_preview("실시간 입력을 시작하면 미리보기 새창이 열립니다.")
            self.close_preview_window()
        print(self.source)

    def update_datasize(self, index):
        selection = self.comboBox_data.itemText(index)
        if selection == "선택하세요":
            self.datasize = None
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
        print(self.datasize)

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
        print(self.imgsz)

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
        print(self.percentage)

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
        print(f"선택된 장치: {self.device}")

    def update_juso(self, text):
        """사용자가 lineEdit_juso에 입력한 텍스트를 저장하는 함수"""
        normalized_text = text.strip()

        if normalize_source_name(self.source) == CAPTURE_BOARD_SOURCE:
            self.juso = normalized_text if normalized_text else None
        else:
            self.juso = text if normalized_text else None

    def browse_files(self):
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

    def browse_folders(self):
        if self.source == VIDEO_FILE_SOURCE:
            QMessageBox.information(self, "입력 안내", "영상은 파일 하나를 선택해 주세요.")
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
        else:
            print("폴더가 선택되지 않았습니다.")

    def count_image_files(self, folder_path):
        """폴더 안의 이미지 파일 개수를 반환합니다."""
        folder = Path(folder_path)

        if folder.is_dir():
            # 폴더 안에서 이미지 파일 개수를 확인
            image_files = [
                file for file in folder.glob("*") if file.suffix.lower() in IMAGE_EXTENSIONS
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
        self.worker = DetectionWorker(params)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.handle_result)  # 실시간 결과 처리 필요 시
        self.worker.error_signal.connect(self.handle_error)
        self.worker.finished_signal.connect(self.on_detection_finished)
        self.worker.log_signal.connect(self.log_message)
        self.worker.frame_signal.connect(self.update_preview_frame)
        self.worker.finished.connect(self.on_worker_thread_finished)

        # 진행률 다이얼로그 설정
        if self.source == "사진":
            self.progress_dialog = QProgressDialog(
                "AI 객체 탐지를 준비하는 중입니다...", "취소", 0, params["file_count"], self
            )
            self.progress_dialog.setWindowTitle("AI 객체 탐지 진행 중")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.canceled.connect(self.cancel_detection)
            self.progress_dialog.show()
        elif is_live_video_source(self.source):
            self.progress_dialog = QProgressDialog(
                "실시간 탐지 실행 중입니다...", "취소", 0, 0, self
            )
            self.progress_dialog.setWindowTitle("실시간 탐지 진행 중")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.canceled.connect(self.cancel_detection)
            self.progress_dialog.show()
            self.reset_preview("실시간 영상 입력을 연결하는 중입니다.")
            self.show_preview_window("실시간 영상 입력을 연결하는 중입니다.")

        # 스레드 시작
        self.worker.start()

        # 메모리 모니터링
        self.memory_monitor.log_memory_usage("작업 스레드 시작됨")

    @Slot(int, str)
    def update_progress(self, value, message):
        """진행률 업데이트"""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    @Slot(str)
    def handle_error(self, error_msg):
        """에러 처리"""
        if self.preview_window is not None:
            self.preview_window.set_status("실시간 탐지 중 오류가 발생했습니다.")
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()
        self.close_preview_window()
        if not self._close_after_worker:
            QMessageBox.critical(self, "작업 오류", f"작업 중 오류가 발생했습니다:\n{error_msg}")

    @Slot(dict)
    def handle_result(self, result):
        """중간 결과 처리 (필요 시)"""
        pass

    @Slot(str)
    def log_message(self, msg):
        """로그 메시지 처리"""
        print(f"[Worker] {msg}")

    @Slot(dict)
    def on_detection_finished(self, result):
        """작업 완료 처리"""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        if is_live_video_source(result["source"]):
            if self.preview_window is not None:
                self.preview_window.set_status("실시간 탐지가 종료되었습니다.")

        if self._close_after_worker:
            return

        if result.get("status") == "cancelled":
            QMessageBox.information(
                self,
                "AI 객체 탐지 취소",
                (
                    "작업이 취소되었습니다.\n\n"
                    f"취소 전 처리량: {result.get('processed_count', 0)}\n"
                    f"보존된 결과 파일: {len(result.get('output_files', []))}개"
                ),
            )
            return

        self.display_results_new(result)

        original_files = result.get("original_files", [])
        if result["source"] == "사진" and original_files:
            reply = QMessageBox.question(
                self,
                "GPS 정보 분석",
                "이번 작업에서 탐지된 사진의 GPS 정보를 분석하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                gps2.process_image_paths(original_files)

        self.memory_monitor.log_memory_usage("작업 완료")

    def display_results_new(self, result):
        """Show a source-aware summary for a completed detection run."""
        source = result["source"]
        image_count = result["image_count"]
        detected_files = result["detected_files"]
        folder_status = result["folder_status"]
        execution_time = result["execution_time"]
        total_people = result["total_people"]
        total_cars = result["total_cars"]
        output_files = result.get("output_files", [])
        errors = result.get("errors", [])

        if is_live_video_source(source):
            message = (
                f"{folder_status}\n\n"
                f"영상 탐지가 종료되었고, 실행 시간은 {execution_time:.2f}초입니다."
            )
            if self.only_person and not self.only_car:
                message += f"\n\n최대 동시 사람 탐지 수: {total_people}명"
            elif self.only_car and not self.only_person:
                message += f"\n\n최대 동시 차량 탐지 수: {total_cars}대"
            else:
                message += f"\n\n최대 동시 탐지 수: 사람 {total_people}명, 차량 {total_cars}대"

            if output_files:
                message += f"\n결과 영상: {output_files[0]}"
        else:
            message = (
                f"{folder_status}\n\n"
                f"총 사진 {image_count}장 중 {len(detected_files)}장에서 객체가 탐지되었고, "
                f"실행 시간은 {execution_time:.2f}초입니다."
            )

            if detected_files:
                if self.only_person and not self.only_car:
                    message += f"\n\n사람 탐지 수: {total_people}명"
                elif self.only_car and not self.only_person:
                    message += f"\n\n차량 탐지 수: {total_cars}대"
                else:
                    message += f"\n\n탐지 결과: 사람 {total_people}명, 차량 {total_cars}대"

                message += f"\n탐지 결과 폴더: {result.get('output_folder', DETECTED_OUTPUT_DIR)}"
            else:
                message += "\n\n탐지된 사람 또는 차량이 없습니다."

        if errors:
            message += f"\n\n처리하지 못한 항목: {len(errors)}개"

        QMessageBox.information(self, "AI 객체 탐지 완료", message)


if __name__ == "__main__":
    Ui_MainWindow.run_app()
