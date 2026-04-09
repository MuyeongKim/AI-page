###############################################################################################
#  ______     __                                  __    __                   ______   ______  #
# /      \   /  |                                /  |  /  |                 /      \ /      | #
#/$$$$$$  | _$$ |_     ______   __    __         $$ |  $$ |  ______        /$$$$$$  |$$$$$$/  # 
#$$ \__$$/ / $$   |   /      \ /  |  /  | ______ $$ |  $$ | /      \       $$ |__$$ |  $$ |   # 
#$$      \ $$$$$$/    $$$$$$  |$$ |  $$ |/      |$$ |  $$ |/$$$$$$  |      $$    $$ |  $$ |   # 
# $$$$$$  |  $$ | __  /    $$ |$$ |  $$ |$$$$$$/ $$ |  $$ |$$ |  $$ |      $$$$$$$$ |  $$ |   # 
#/  \__$$ |  $$ |/  |/$$$$$$$ |$$ \__$$ |        $$ \__$$ |$$ |__$$ |      $$ |  $$ | _$$ |_  # 
#$$    $$/   $$  $$/ $$    $$ |$$    $$ |        $$    $$/ $$    $$/       $$ |  $$ |/ $$   | #
# $$$$$$/     $$$$/   $$$$$$$/  $$$$$$$ |         $$$$$$/  $$$$$$$/        $$/   $$/ $$$$$$/  # 
#                              /  \__$$ |                  $$ |                               # 
#                              $$    $$/                   $$ |                               #
#                               $$$$$$/                    $$/                                #
#                                                                                             #  
###############################################################################################
#-----------------------------------------------------------------------------
# 🚀 메모리 최적화 업데이트 (2025.08.10)
# - 메모리 모니터링 시스템 통합 (memory_monitor.py)  
# - FPS 버퍼를 collections.deque로 최적화 (O(1) 성능)
# - 실시간 처리 루프에 주기적 메모리 정리 추가 (100프레임마다)
# - 프로그램 종료 시 메모리 사용량 요약 출력
# - 매 프레임마다 YOLO 결과 객체 즉시 해제로 메모리 누수 방지
#-----------------------------------------------------------------------------


import sys
import torch
import os
import shutil 
import time
import gc  # 가비지 컬렉터 추가
from pathlib import Path
from collections import deque  # 메모리 효율적인 FPS 버퍼용
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
from ultralytics import YOLO
from mypackage import start, gps2
from mypackage.modern_gui_fixed import ModernUi_MainWindow
import cv2  # OpenCV 추가
import numpy as np # Numpy 추가

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
        def __init__(self): pass
        def log_memory_usage(self, context=""): pass
        def get_summary(self): return "모니터링 비활성화"


class DetectionWorker(QThread):
    """
    YOLO 객체 탐지를 백그라운드에서 수행하는 워커 스레드
    """
    # 시그널 정의
    progress_signal = Signal(int, str)  # 진행률 (퍼센트/카운트, 메시지)
    result_signal = Signal(dict)        # 탐지 결과 데이터
    log_signal = Signal(str)            # 로그 메시지
    error_signal = Signal(str)          # 에러 메시지
    finished_signal = Signal(dict)      # 작업 완료 시그널 (최종 결과 포함)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.is_running = True
        self.model = None
        
        # 파라미터 언패킹
        self.source = params.get('source')
        self.juso = params.get('juso')
        self.datasize = params.get('datasize')
        self.imgsz = params.get('imgsz')
        self.percentage = params.get('percentage')
        self.device = params.get('device')
        self.classes_to_detect = params.get('classes_to_detect')
        self.file_count = params.get('file_count', 0)
        self.only_person = params.get('only_person', False)
        self.only_car = params.get('only_car', False)
        
        # 카운터 초기화
        self.total_people_detected = 0
        self.total_cars_detected = 0

    def run(self):
        try:
            start_time = time.time()
            self.log_signal.emit("🚀 작업 스레드 시작")
            
            # 모델 로드
            self.log_signal.emit(f"모델 로딩 중: {self.datasize}")
            self.model = YOLO(self.datasize)
            
            # 결과 저장용 변수
            detected_files = []
            output_folder = "detected_files"
            
            # 폴더 생성
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                folder_status = "새로운 폴더(detected_files)가 생성되었습니다."
            else:
                folder_status = "폴더(detected_files)가 이미 존재합니다."

            # 소스 유형에 따른 처리
            if self.source == '사진':
                self.process_images(output_folder, detected_files)
            elif self.source in ['영상', '외부영상(캡쳐보드)']:
                self.process_video(output_folder)
                
            # 최종 결과 정리
            end_time = time.time()
            execution_time = end_time - start_time
            
            final_result = {
                'source': self.source,
                'image_count': self.file_count if self.source == '사진' else 0,
                'detected_files': detected_files,
                'folder_status': folder_status,
                'execution_time': execution_time,
                'total_people': self.total_people_detected,
                'total_cars': self.total_cars_detected
            }
            
            self.finished_signal.emit(final_result)
            
        except Exception as e:
            self.error_signal.emit(str(e))
            
    def stop(self):
        """작업 중지 요청"""
        self.is_running = False

    def process_images(self, output_folder, detected_files):
        """이미지 파일 처리 로직"""
        if isinstance(self.juso, Path):
            sources = [str(self.juso)]
        elif isinstance(self.juso, list):
            sources = [str(path) for path in self.juso]
        else:
            return

        processed_count = 0
        
        for source in sources:
            if not self.is_running: break
            
            if os.path.isdir(source):
                files_in_folder = [str(file) for file in Path(source).glob("*") if file.is_file()]
                for file in files_in_folder:
                    if not self.is_running: break
                    
                    self.process_single_file(file, detected_files, output_folder)
                    processed_count += 1
                    self.progress_signal.emit(processed_count, f"진행 중... {processed_count} / {self.file_count}")
                    
            elif os.path.isfile(source):
                self.process_single_file(source, detected_files, output_folder)
                processed_count += 1
                self.progress_signal.emit(processed_count, f"진행 중... {processed_count} / {self.file_count}")

    def process_single_file(self, source, detected_files, output_folder):
        """단일 파일 YOLO 처리"""
        try:
            results = self.model(source, stream=True, imgsz=self.imgsz, save=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)

            people_count, car_count = 0, 0

            for result in results:
                try:
                    detected_classes = result.names
                    detected_ids = result.boxes.cls

                    people_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person')
                    car_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] in ['car', 'bus', 'truck'])

                    if people_count > 0 or car_count > 0:
                        detected_files.append(source)
                        self.total_people_detected += people_count
                        self.total_cars_detected += car_count
                        self.file_copy(source, result, output_folder)
                finally:
                    del result
            
            # 메모리 정리 (10개마다)
            if len(detected_files) % 10 == 0:
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
        except Exception as e:
            print(f"⚠️ 파일 처리 오류 ({source}): {e}")

    def process_video(self, output_folder):
        """비디오/캡쳐보드 처리 로직"""
        cap = None
        out = None
        should_save_video = (self.source == '영상')
        output_video_filename = None

        try:
            if self.source == '영상':
                source_path = str(self.juso[0]) if isinstance(self.juso, list) else str(self.juso)
                output_video_filename = os.path.join(output_folder, f"detected_{os.path.basename(source_path)}")
            else:
                source_path = 0

            cap = cv2.VideoCapture(source_path)
            if not cap.isOpened():
                raise Exception("카메라 또는 영상을 열 수 없습니다.")

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            if should_save_video:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                out = cv2.VideoWriter(output_video_filename, fourcc, fps, (frame_width, frame_height))

            fps_buffer = deque(maxlen=10)
            frame_counter = 0
            
            # 창 설정 (메인 스레드가 아니므로 여기서 cv2 창을 띄우는 것은 주의가 필요하지만, 
            # cv2.imshow는 메인 스레드가 아니어도 동작하는 경우가 많음. 
            # 하지만 안전을 위해 cv2 관련 작업은 여기서 하되, GUI 이벤트 루프와의 충돌을 조심해야 함.
            # PySide6와 cv2.imshow를 같이 쓸 때는 보통 별도 스레드에서 cv2.imshow를 호출해도 됨)
            
            cv2.namedWindow("Real-time Detection (Press 'q' to quit)", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Real-time Detection (Press 'q' to quit)", 1280, 720)

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                results_list = self.model(frame, imgsz=self.imgsz, verbose=False, conf=self.percentage, device=self.device, classes=self.classes_to_detect)
                
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
                            if cls_name == 'person': person_count += 1
                            elif cls_name in ['car', 'bus', 'truck']: car_count += 1

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

                    cv2.imshow("Real-time Detection (Press 'q' to quit)", im_array)
                    
                    if should_save_video and out is not None:
                        out.write(im_array)

                    # 메모리 정리
                    del result
                    del results_list

                frame_counter += 1
                if frame_counter % 100 == 0:
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as e:
            raise e
        finally:
            if cap: cap.release()
            if out: out.release()
            cv2.destroyAllWindows()
            gc.collect()

    def draw_info(self, img, fps_text, person_count, car_count):
        """화면에 정보 표시"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, fps_text, (10, 30), font, 0.7, (0, 255, 0), 2)
        cv2.putText(img, f"Person: {person_count}", (10, 60), font, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Car: {car_count}", (10, 90), font, 0.7, (255, 255, 255), 2)

    def file_copy(self, source, result, output_folder):
        """파일 복사 헬퍼"""
        original_destination = os.path.join(output_folder, "original_" + os.path.basename(source))
        result_dir = Path(result.save_dir)
        result_file = result_dir / os.path.basename(source)

        if os.path.exists(original_destination):
            original_destination = self.get_unique_filename(original_destination)

        shutil.copy(source, original_destination)

        if result_file.exists():
            result_destination = os.path.join(output_folder, "detected_" + os.path.basename(source))
            if os.path.exists(result_destination):
                result_destination = self.get_unique_filename(result_destination)
            shutil.copy(result_file, result_destination)

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
        self.percentage = 0.3
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.imgsz = 1920
        self.only_person = False
        self.only_car = False
        self.classes_to_detect = None
        self.total_people_detected = 0
        self.total_cars_detected = 0
        
        # 메모리 관리용 변수 추가
        self.current_model = None
        
        # 🚀 메모리 모니터링 도구 초기화
        self.memory_monitor = MemoryMonitor()
        self.memory_monitor.log_memory_usage("GUI 초기화 완료")

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
            self.classes_to_detect = [2,5,7]  # 자동차만 탐지(자동차, 버스, 트럭)
            print("차량만 탐지합니다.")
        else:
            self.classes_to_detect = None  # 전체 탐지
            print("전체 객체 탐지를 사용합니다.")

    def update_only_person(self, state):
        """체크박스 상태 변경"""
        self.only_person = state == 2  # 체크되면 True, 아니면 False
        self.update_detection_options()

    def update_only_car(self, state):
        """체크박스 상태 변경"""
        self.only_car = state == 2  # 체크되면 True, 아니면 False
        self.update_detection_options()
    
    def exit_application(self):
        if self.confirm_exit():
            self.close()

    def closeEvent(self, event):
        if self.confirm_exit():
            # 종료 시 메모리 정리
            self.cleanup_resources()
            event.accept()
        else:
            event.ignore()
    
    def cleanup_resources(self):
        """애플리케이션 종료 시 메모리 정리"""
        try:
            # 🚀 메모리 사용량 최종 요약 출력
            if hasattr(self, 'memory_monitor'):
                print("=" * 50)
                print("📊 메모리 사용량 최종 요약")
                print(self.memory_monitor.get_summary())
                print("=" * 50)
            
            # YOLO 모델 메모리 해제
            if self.current_model is not None:
                del self.current_model
                self.current_model = None
                print("🧹 YOLO 모델 메모리 해제 완료")
            
            # CUDA 캐시 정리
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("🧹 CUDA 메모리 캐시 정리 완료")
            
            # 가비지 컬렉션 강제 실행
            gc.collect()
            print("🧹 가비지 컬렉션 완료")
            
            # 🚀 최종 메모리 상태 확인
            if hasattr(self, 'memory_monitor'):
                self.memory_monitor.log_memory_usage("프로그램 종료 시")
            
        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")

    def confirm_exit(self):
        reply = QMessageBox.question(
            self, '종료 확인', '정말로 종료하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return reply == QMessageBox.Yes
            
    def update_source(self, index):
        selection = self.comboBox_source.itemText(index)
        if selection == "선택하세요":
            return ""
        else:
            self.source = selection
        print(self.source)
        
    def update_datasize(self, index):
        selection = self.comboBox_data.itemText(index)
        if selection == "선택하세요":
            return ""
        else:
            size_dict = {
                'YoloV26_최대(추천)': 'yolo26x.pt',
                'YoloV26_대': 'yolo26l.pt',
                'YoloV26_중': 'yolo26m.pt',
                'YoloV26_소': 'yolo26s.pt',
                'YoloV26_최소': 'yolo26n.pt',
                'YoloV11_최대': 'yolo11x.pt',
                'YoloV11_대': 'yolo11l.pt',
                'YoloV11_중': 'yolo11m.pt',
                'YoloV11_소': 'yolo11s.pt',
                'YoloV11_최소': 'yolo11n.pt',
                'YoloV12(최대)': 'yolo12x.pt',
                'YoloV12(최소)': 'yolo12n.pt',
                '화염전용탐지(예정)': 'fire_detect.py'
            }
            self.datasize = size_dict[selection]   
        print(self.datasize)            

    def option_imgsz(self, index):
        selection = self.comboBox_imgsz.itemText(index)
        if selection == "해상도":
            self.imgsz = 1920
        else:
            size_dict = {'640': 640, '1080': 1080, '1280': 1280, '1680': 1680, '1920(기본값)' : 1920, '3000' : 3000, '4000(*)': 4000}        
            self.imgsz = size_dict[selection]  
        print(self.imgsz)          
    
    def option_percentage(self, index):
        selection = self.comboBox_percentage.itemText(index)
        if selection == "신뢰도":
            self.percentage = 0.1
        else:
            size_dict = {'5%': 0.04, '10%(기본값)': 0.1,'15%': 0.15, '20%': 0.2, '30%': 0.3, '50%': 0.5, '80%': 0.8}
            self.percentage = size_dict[selection]  
        print(self.percentage)                 

    def option_device(self, index):
        """GPU/CPU 자동 선택"""
        selection = self.comboBox_device.itemText(index)
        device_options = {'CPU' : 'cpu', 'GPU' : 0}
        selected_device = device_options.get(selection, 'cpu')

        if selected_device == 'cuda' and not torch.cuda.is_available():
            QMessageBox.warning(self, "GPU 사용 불가", "GPU를 사용할 수 없어 CPU로 전환합니다.")
            selected_device = 'cpu'
            
        self.device = selected_device
        print(f"선택된 장치: {self.device}")


    def update_juso(self, text):
        """사용자가 lineEdit_juso에 입력한 텍스트를 저장하는 함수"""
        self.juso = text                         
            
    def browse_files(self):
        # 파일 선택 다이얼로그 열기
        file_paths, _ = QFileDialog.getOpenFileNames(self, "파일 선택")
        if file_paths:  # 사용자가 파일을 선택하면 그 경로들을 lineEdit_juso에 설정
            self.lineEdit_juso.setText(", ".join(file_paths))
            self.juso = file_paths
            self.file_count = len(self.juso)
            if len(self.juso) == 1:
                print(self.juso)
            else:
                print(f"선택한 이미지 파일 수: {len(self.juso)}개")

    def browse_folders(self):
        # 파일 선택 다이얼로그 열기
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
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}  # 이미지 확장자 목록
        folder = Path(folder_path)
        
        if folder.is_dir():
            # 폴더 안에서 이미지 파일 개수를 확인
            image_files = [file for file in folder.glob("*") if file.suffix.lower() in image_extensions]
            return len(image_files)
        else:
            return 0

    def process_file(self, model, source, detected_files, output_folder):
        """YOLO 모델을 실행하고 탐지된 객체를 저장 - 메모리 최적화"""
        try:
            results = model(source, stream=True, imgsz=self.imgsz, save=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)

            people_count, car_count = 0, 0

            for result in results:
                try:
                    detected_classes = result.names
                    detected_ids = result.boxes.cls

                    people_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person')
                    car_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] in ['car', 'bus', 'truck'])

                    if people_count > 0 or car_count > 0:
                        detected_files.append(source)
                        self.total_people_detected += people_count
                        self.total_cars_detected += car_count
                        self.file_copy(source, result, output_folder)
                
                finally:
                    # 결과 객체 메모리 해제
                    del result
                    
            QApplication.processEvents()  # GUI가 멈추지 않도록 함
            
        except Exception as e:
            print(f"⚠️ 파일 처리 오류 ({source}): {e}")
            
        finally:
            # 메모리 정리 - 대용량 파일 처리 후
            if len(detected_files) % 10 == 0:  # 10개 파일마다 메모리 정리
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    def file_copy(self, source, result, output_folder):
        """탐지된 이미지 파일을 복사 (덮어쓰기 방지)"""
        original_destination = os.path.join(output_folder, "original_" + os.path.basename(source))
        result_dir = Path(result.save_dir)
        result_file = result_dir / os.path.basename(source)

        if os.path.exists(original_destination):
            original_destination = self.get_unique_filename(original_destination)

        shutil.copy(source, original_destination)

        if result_file.exists():
            result_destination = os.path.join(output_folder, "detected_" + os.path.basename(source))
            if os.path.exists(result_destination):
                result_destination = self.get_unique_filename(result_destination)
            shutil.copy(result_file, result_destination)

    def get_unique_filename(self, file_path):
        """덮어쓰지 않도록 새로운 파일명 생성"""
        base, ext = os.path.splitext(file_path)
        counter = 1
        while os.path.exists(file_path):
            file_path = f"{base}_{counter}{ext}"
            counter += 1
        return file_path

    def display_results(self, image_count, sources, detected_files, folder_status, execution_time):
        """탐지 결과를 팝업 메시지로 표시"""
            # 🔹 기본값 설정
        message = f"{folder_status}\n\n 총 탐지파일 {image_count}장 중 {len(detected_files)}개 객체탐지, 실행 시간: {execution_time} 초"
        if detected_files:
            total_images = image_count if isinstance(self.juso, Path) else len(sources)
            if self.only_person and not self.only_car:
                message = (
                    f"{folder_status}\n\n"
                    f"선택한 사진파일 총 {total_images}장 중 {self.total_people_detected}명 탐지되었으며 \n 👤사람이 탐지된 파일 수 : {len(detected_files)}개\n"
                    f"탐지된 파일(원본 및 결과파일)은 detected_files 폴더에 저장되었습니다.\n\n"
                    f"탐지에 걸린 시간은 {execution_time:.2f}초 입니다."
                )
            elif self.only_car and not self.only_person:
                message = (
                    f"{folder_status}\n\n"
                    f"선택한 사진파일 총 {total_images}장 중 {self.total_cars_detected}대가 탐지되었으며 \n 🚗자동차가 탐지된 파일 수 : {len(detected_files)}개\n"
                    f"탐지된 파일(원본 및 결과파일)은 detected_files 폴더에 저장되었습니다.\n\n"
                    f"탐지에 걸린 시간은 {execution_time:.2f}초 입니다."
                )    
            elif self.only_person and self.only_car:
                message = (
                    f"{folder_status}\n\n"
                    f"선택한 사진파일 총 {total_images}장 중 객체(👤 사람: {self.total_people_detected}명, 🚗자동차: {self.total_cars_detected}대)가 \n탐지된 파일 수 : {len(detected_files)}개\n"
                    f"탐지된 파일(원본 및 결과파일)은 detected_files 폴더에 저장되었습니다.\n\n"
                    f"탐지에 걸린 시간은 {execution_time:.2f}초 입니다."
                )    
        else:
            message = (
                f"{folder_status}\n\n"
                f"사진에서 사람이 탐지되지 않았습니다."
            )
        
        QMessageBox.information(
            None, "AI 객체 탐지 완료", message)


    def submit(self):
        """실행 버튼 클릭 시 호출 - 스레드 시작"""
        # 중복 실행 방지
        if hasattr(self, 'worker') and self.worker.isRunning():
            QMessageBox.warning(self, "작업 안내", "이미 작업이 진행 중입니다.")
            return

        # 입력값 검증
        if self.source == '사진':
            if not self.juso:
                QMessageBox.warning(None, "입력 확인", "올바른 파일 또는 폴더를 선택해 주세요.")
                return
        
        # 파라미터 패키징
        params = {
            'source': self.source,
            'juso': self.juso,
            'datasize': self.datasize,
            'imgsz': self.imgsz,
            'percentage': self.percentage,
            'device': self.device,
            'classes_to_detect': self.classes_to_detect,
            'file_count': getattr(self, 'file_count', 0),
            'only_person': self.only_person,
            'only_car': self.only_car
        }

        # 워커 스레드 생성 및 연결
        self.worker = DetectionWorker(params)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.handle_result) # 실시간 결과 처리 필요 시
        self.worker.error_signal.connect(self.handle_error)
        self.worker.finished_signal.connect(self.on_detection_finished)
        self.worker.log_signal.connect(self.log_message)
        
        # 진행률 다이얼로그 설정 (사진인 경우)
        if self.source == '사진':
            self.progress_dialog = QProgressDialog("AI 객체 탐지를 준비하는 중입니다...", "취소", 0, params['file_count'], self)
            self.progress_dialog.setWindowTitle("AI 객체 탐지 진행 중")
            self.progress_dialog.setWindowModality(Qt.ApplicationModal)
            self.progress_dialog.canceled.connect(self.worker.stop)
            self.progress_dialog.show()

        # 스레드 시작
        self.worker.start()
        
        # 메모리 모니터링
        self.memory_monitor.log_memory_usage("작업 스레드 시작됨")

    @Slot(int, str)
    def update_progress(self, value, message):
        """진행률 업데이트"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    @Slot(str)
    def handle_error(self, error_msg):
        """에러 처리"""
        QMessageBox.critical(self, "작업 오류", f"작업 중 오류가 발생했습니다:\n{error_msg}")
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

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
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            
        execution_time = result['execution_time']
        detected_files = result['detected_files']
        folder_status = result['folder_status']
        
        # 결과 메시지 표시
        self.display_results_new(result)
        
        # GPS 처리 확인 (사진인 경우)
        if result['source'] == '사진' and len(detected_files) > 0:
            reply = QMessageBox.question(self, "GPS 정보 분석", "탐지된 파일을 기준으로 GPS 정보를 분석하시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                gps2.process_images_in_folder("detected_files")

        # 메모리 정리
        self.cleanup_resources()

    def display_results_new(self, result):
        """결과 표시 (리팩토링됨)"""
        source = result['source']
        image_count = result['image_count']
        detected_files = result['detected_files']
        folder_status = result['folder_status']
        execution_time = result['execution_time']
        total_people = result['total_people']
        total_cars = result['total_cars']

        message = f"{folder_status}\n\n 총 탐지파일 {image_count}장 중 {len(detected_files)}개 객체탐지, 실행 시간: {execution_time:.2f} 초"
        
        if detected_files:
            if self.only_person and not self.only_car:
                message += f"\n👤 사람 탐지: {total_people}명"
            elif self.only_car and not self.only_person:
                message += f"\n🚗 자동차 탐지: {total_cars}대"
            else:
                message += f"\n객체(👤 {total_people}명, 🚗 {total_cars}대)"
                
            message += "\n\n탐지된 파일은 detected_files 폴더에 저장되었습니다."
        else:
            message += "\n\n탐지된 객체가 없습니다."

        QMessageBox.information(self, "AI 객체 탐지 완료", message)
        """GUI 실행 함수"""
        app = QApplication.instance()  # 기존 QApplication이 있으면 가져오기
        if app is None:
            app = QApplication(sys.argv)  # 없으면 새로 생성

        if start.authenticate():  # 인증 확인
            window = Ui_MainWindow()
            window.show()
            sys.exit(app.exec())
        else:
            sys.exit()  # 인증 실패 시 종료

def _display_results_new_fixed(self, result):
    """Display the final detection summary without re-entering app startup."""
    image_count = result['image_count']
    detected_files = result['detected_files']
    folder_status = result['folder_status']
    execution_time = result['execution_time']
    total_people = result['total_people']
    total_cars = result['total_cars']

    message = (
        f"{folder_status}\n\n"
        f"총 처리 파일 {image_count}개 중 {len(detected_files)}개에서 객체가 탐지되었고, "
        f"실행 시간은 {execution_time:.2f}초입니다."
    )

    if detected_files:
        if self.only_person and not self.only_car:
            message += f"\n\n사람 탐지 수: {total_people}명"
        elif self.only_car and not self.only_person:
            message += f"\n\n차량 탐지 수: {total_cars}대"
        else:
            message += f"\n\n탐지 결과: 사람 {total_people}명, 차량 {total_cars}대"

        message += "\n탐지된 파일은 detected_files 폴더에 저장되었습니다."
    else:
        message += "\n\n탐지된 객체가 없습니다."

    QMessageBox.information(self, "AI 객체 탐지 완료", message)


Ui_MainWindow.display_results_new = _display_results_new_fixed


if __name__ == "__main__":
    Ui_MainWindow.run_app()
