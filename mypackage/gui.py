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
 

import sys
import torch
import os
import shutil 
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt
from ultralytics import YOLO
from mypackage import start, gps2
from mypackage.ex_gui import Ui_MainWindow
import cv2  # OpenCV 추가
import numpy as np # Numpy 추가


class Ui_MainWindow(QMainWindow, Ui_MainWindow):
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

    def update_detection_options(self):
        """체크박스 상태에 따라 탐지 옵션을 업데이트"""
        if self.only_person and self.only_car:
            self.classes_to_detect = [0, 2, 5, 7]  # 사람과 자동차 탐지(자동차, 버스, 트럭)
            print("사람 및 자동차 탐지 활성화")
        elif self.only_person:
            self.classes_to_detect = [0]  # 사람만 탐지
            print("사람만 탐지 활성화")
        elif self.only_car:
            self.classes_to_detect = [2,5,7]  # 자동차만 탐지(자동차, 버스, 트럭)
            print("자동차만 탐지 활성화")
        else:
            self.classes_to_detect = None  # 전체 탐지
            print("전체 탐지 활성화")

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
            event.accept()
        else:
            event.ignore()

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
            size_dict = {'YoloV11_최대(추천)' : 'yolo11x.pt', 'YoloV11_대': 'yolo11l.pt', 'YoloV11_중': 'yolo11m.pt', 'YoloV11_소': 'yolo11s.pt', 'YoloV11_최소': 'yolo11n.pt', 'YoloV12(최대)': 'yolo12x.pt', 'YoloV12(최소)': 'yolo12n.pt', 'YoloV8(최대)': 'yolov8x.pt', 'VisDrone(예정)': 'visdrone.pt', '화염전용탐지(예정)' :'fire_detect.py'}
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
            QMessageBox.warning(self, "GPU 사용 불가", "GPU가 없어 CPU로 전환됩니다.")
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
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"}  # 이미지 확장자 목록
        folder = Path(folder_path)
        
        if folder.is_dir():
            # 폴더 안에서 이미지 파일 개수를 확인
            image_files = [file for file in folder.glob("*") if file.suffix.lower() in image_extensions]
            return len(image_files)
        else:
            return 0

    def process_file(self, model, source, detected_files, output_folder):
        """YOLO 모델을 실행하고 탐지된 객체를 저장"""
        results = model(source, stream=True, imgsz=self.imgsz, save=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)

        people_count, car_count = 0, 0

        for result in results:
            detected_classes = result.names
            detected_ids = result.boxes.cls

            people_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person')
            car_count = sum(1 for cls_id in detected_ids if detected_classes[int(cls_id)] in ['car', 'bus', 'truck'])

            if people_count > 0 or car_count > 0:
                detected_files.append(source)
                self.total_people_detected += people_count
                self.total_cars_detected += car_count
                self.file_copy(source, result, output_folder)

        QApplication.processEvents()  # GUI가 멈추지 않도록 함

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
            None, "AI 객체 탐지 완료 with Stay Up", message) 


    def submit(self):       
        start_time = time.time()  # 시작 시간 기록
        model = YOLO(self.datasize)

        # 결과를 저장할 변수 초기화
        detected_files = []

        # 새 폴더 생성 및 상태 표시
        output_folder = "detected_files"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            folder_status = "새로운 폴더(detected_files)가 생성되었습니다."
        else:
            folder_status = "폴더(detected_files)가 이미 존재합니다."

        # 사진 처리 로직 (이 부분은 변경되지 않았습니다)
        if self.source == '사진':
            if isinstance(self.juso, Path):
                sources = [str(self.juso)]
                image_count = self.count_image_files(self.juso)
            elif isinstance(self.juso, list):
                sources = [str(path) for path in self.juso]
                image_count = len(sources)
            else:
                QMessageBox.warning(None, "오류", "올바른 파일이나 폴더를 선택해주세요.")
                return

            progress_dialog = QProgressDialog(f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n 0 / {self.file_count}", "취소", 0, self.file_count, self)
            progress_dialog.setWindowTitle("AI객체탐지 진행 확인창")
            progress_dialog.setWindowModality(Qt.ApplicationModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            processed_count = 0

            for source in sources:
                if os.path.isdir(source):
                    files_in_folder = [str(file) for file in Path(source).glob("*") if file.is_file()]
                    for file in files_in_folder:
                        if progress_dialog.wasCanceled():
                            break
                        self.process_file(model, file, detected_files, output_folder)
                        processed_count += 1
                        progress_dialog.setValue(processed_count)
                        progress_dialog.setLabelText(f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n {processed_count} / {self.file_count}")
                    if progress_dialog.wasCanceled():
                        break
                elif os.path.isfile(source):
                    self.process_file(model, source, detected_files, output_folder)
                    processed_count += 1
                    progress_dialog.setValue(processed_count)
                    progress_dialog.setLabelText(f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n {processed_count} / {self.file_count}")
                else:
                    print(f"올바르지 않은 경로: {source}")

            progress_dialog.close()

            end_time = time.time()
            execution_time = end_time - start_time
            print(f"총 탐지파일 {image_count}장 중 {len(detected_files)}개 객체탐지, 실행 시간: {execution_time} 초")
            self.display_results(image_count, sources, detected_files, folder_status, execution_time)

            if len(detected_files) > 0:
                reply = QMessageBox.question(self, "GPS 정보 처리", "GPS 정보 분석을 실행하시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    gps2.process_images_in_folder(output_folder)
            else:
                print("탐지된 객체가 없어 GPS 분석을 생략합니다.")

        # 영상 또는 외부영상(캡쳐보드) 처리 로직 (카운트 로직 수정)
        elif self.source in ['영상', '외부영상(캡쳐보드)']:
            cap = None
            out = None # VideoWriter 객체 초기화
            should_save_video = (self.source == '영상') # '영상'일 때만 저장하도록 플래그 설정

            try:
                if self.source == '영상':
                    source_path = str(self.juso[0]) if isinstance(self.juso, list) else str(self.juso)
                    # 출력 비디오 파일명 설정 (예: 원본_detected.mp4)
                    output_video_filename = os.path.join(output_folder, f"detected_{os.path.basename(source_path)}")
                else: # '외부영상(캡쳐보드)'
                    source_path = 0
                    # 웹캠 캡처는 저장하지 않으므로 파일명은 필요 없지만, 변수 할당을 위해 유지
                    output_video_filename = None 

                cap = cv2.VideoCapture(source_path)

                if not cap.isOpened():
                    QMessageBox.warning(self, "카메라/영상 로드 실패", "지정된 카메라 또는 영상을 열 수 없습니다. 다른 인덱스를 시도하거나 다른 응용 프로그램이 카메라를 사용 중인지 확인하세요.")
                    return

                # 원본 영상의 정보 가져오기
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                # '영상'일 경우에만 출력 비디오 파일 설정
                if should_save_video:
                    # MP4V 코덱 사용 (Windows에서는 'mp4v' 대신 'DIVX' 또는 'XVID'도 가능)
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # 비디오 코덱 설정
                    
                    # output_folder가 없으면 생성 (이미 위에서 처리했지만 한 번 더 확인)
                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)

                    out = cv2.VideoWriter(output_video_filename, fourcc, fps, (frame_width, frame_height))

                    if not out.isOpened():
                        QMessageBox.warning(self, "비디오 저장 오류", "출력 비디오 파일을 열 수 없습니다. 코덱 문제가 있을 수 있습니다.")
                        # 저장하지 못하더라도 계속 탐지는 진행하도록 out을 None으로 설정
                        out = None 
                        should_save_video = False # 저장 실패 시 플래그 끄기

                fps_buffer = []
                fps_buffer_size = 10

                QMessageBox.information(self, "영상 탐지 시작", "영상 탐지를 시작합니다. 'q' 키를 누르면 종료됩니다.")

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        print("프레임을 읽을 수 없습니다. 스트림 종료.")
                        break

                    # YOLO 모델로 프레임 추론 (verbose=True로 설정하여 콘솔 출력 활성화)
                    results_list = model(frame, imgsz=self.imgsz, verbose=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)
                    
                    if len(results_list) > 0:
                        result = results_list[0]
                        im_array = result.plot() # 탐지 결과를 프레임에 그림

                        # ########## 카운트 로직 시작 ##########
                        person_count = 0
                        car_count = 0

                        if result.boxes is not None:
                            for box in result.boxes:
                                class_id = int(box.cls.item())
                                class_name = result.names[class_id]
                                
                                if class_name == 'person':
                                    person_count += 1
                                elif class_name in ['car', 'bus', 'truck']:
                                    car_count += 1
                        # ########## 카운트 로직 끝 ##########

                        # FPS 계산 및 텍스트 준비
                        frame_time_ms = sum(result.speed.values())
                        if frame_time_ms > 0:
                            fps_current = 1000 / frame_time_ms
                            fps_buffer.append(fps_current)
                            if len(fps_buffer) > fps_buffer_size:
                                fps_buffer.pop(0)
                            avg_fps = np.mean(fps_buffer)
                            fps_text = f"FPS: {avg_fps:.2f}"
                        else:
                            fps_text = "FPS: N/A"

                        person_display_text = f"Person: {person_count}"
                        car_display_text = f"Car: {car_count}"

                        # 텍스트 설정
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.7
                        thickness = 2
                        padding = 5
                        y_offset = 20
                        x_start = 10

                        # --- FPS 표시 ---
                        fps_bg_color = (50, 50, 50) # 어두운 회색
                        fps_text_color = (0, 255, 0) # 밝은 녹색
                        (text_width, text_height), baseline = cv2.getTextSize(fps_text, font, font_scale, thickness)
                        org = (x_start, y_offset + text_height)
                        cv2.rectangle(im_array, (x_start - padding, y_offset - padding),
                                    (x_start + text_width + padding, y_offset + text_height + padding), fps_bg_color, -1)
                        cv2.putText(im_array, fps_text, org, font, font_scale, fps_text_color, thickness, cv2.LINE_AA)
                        y_offset += text_height + 2 * padding + 5 # 다음 텍스트를 위한 Y 오프셋 조정

                        # --- Person Count 표시 ---
                        person_bg_color = (100, 0, 0) # 어두운 빨간색
                        person_text_color = (255, 255, 255) # 흰색
                        (text_width, text_height), baseline = cv2.getTextSize(person_display_text, font, font_scale, thickness)
                        org = (x_start, y_offset + text_height)
                        cv2.rectangle(im_array, (x_start - padding, y_offset - padding),
                                    (x_start + text_width + padding, y_offset + text_height + padding), person_bg_color, -1)
                        cv2.putText(im_array, person_display_text, org, font, font_scale, person_text_color, thickness, cv2.LINE_AA)
                        y_offset += text_height + 2 * padding + 5

                        # --- Car Count 표시 ---
                        car_bg_color = (0, 0, 150) # 어두운 파란색
                        car_text_color = (255, 255, 255) # 흰색
                        (text_width, text_height), baseline = cv2.getTextSize(car_display_text, font, font_scale, thickness)
                        org = (x_start, y_offset + text_height)
                        cv2.rectangle(im_array, (x_start - padding, y_offset - padding),
                                    (x_start + text_width + padding, y_offset + text_height + padding), car_bg_color, -1)
                        cv2.putText(im_array, car_display_text, org, font, font_scale, car_text_color, thickness, cv2.LINE_AA)

                        # 화면 표시
                        cv2.imshow("Real-time Detection (Press 'q' to quit)", im_array)
                        
                        # '영상'일 경우에만 탐지된 프레임 비디오 파일로 저장
                        if should_save_video and out is not None:
                            out.write(im_array)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            except Exception as e:
                print(f"영상 처리 중 오류 발생: {e}")
                QMessageBox.critical(self, "오류", f"영상 처리 중 오류가 발생했습니다: {e}")
            finally:
                # --- 중요: 자원 해제 ---
                if cap is not None and cap.isOpened():
                    cap.release() # 카메라/비디오 자원 해제
                if out is not None and out.isOpened(): # out이 None이 아닐 때만 release
                    out.release() # 비디오 저장기 자원 해제
                cv2.destroyAllWindows() # 모든 OpenCV 창 닫기
                # ----------------------

            end_time = time.time()
            execution_time = end_time - start_time
            print(f"총 실행 시간: {execution_time:.2f} 초")
            
            # '영상'일 경우에만 저장 완료 메시지 표시
            if should_save_video and output_video_filename:
                QMessageBox.information(self, "영상 탐지 완료", f"영상 탐지가 완료되었습니다. 탐지된 영상은 '{output_video_filename}'에 저장되었습니다.\n총 실행 시간: {execution_time:.2f}초")
            else: # 캡처보드이거나 저장에 실패했을 경우
                QMessageBox.information(self, "영상 탐지 완료", f"영상 탐지가 완료되었습니다. (저장되지 않음)\n총 실행 시간: {execution_time:.2f}초")

  

    def run_app():
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

if __name__ == "__main__":
    Ui_MainWindow.run_app()
