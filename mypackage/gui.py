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
            size_dict = {'최대(추천)' : 'yolo11x.pt', '대': 'yolo11l.pt', '중': 'yolo11m.pt', '소': 'yolo11s.pt', '최소': 'yolo11n.pt', 'Yolo V12(최대)': 'yolo12x.pt', 'Yolo V12(최소)': 'yolo12n.pt', 'YoloV8(최대)': 'yolov8x.pt', 'VisDrone(예정)': 'visdrone.pt', '화염전용탐지(예정)' :'fire_detect.py'}
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
        detected_files = []  # 'person'이 감지된 파일 이름을 저장

        
        # 새 폴더 생성 및 상태 표시
        output_folder = "detected_files"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            folder_status = "새로운 폴더(detected_files)가 생성되었습니다."
        else:
            folder_status = "폴더(detected_files)가 이미 존재합니다."
       

        # 사진 처리 로직
        if self.source == '사진':
            # 파일과 폴더 구분 및 리스트 형태로 통합
            if isinstance(self.juso, Path):
                sources = [str(self.juso)]  # Path -> str 변환
                image_count = self.count_image_files(self.juso)  # 폴더의 이미지 파일 개수 계산
            elif isinstance(self.juso, list):
                sources = [str(path) for path in self.juso]
                image_count = len(sources)  # 파일 목록 길이를 이미지 개수로 설정
            else:
                QMessageBox.warning(None, "오류", "올바른 파일이나 폴더를 선택해주세요.")
                return
            # 진행률 팝업창 초기화
            progress_dialog = QProgressDialog("사진파일에 대한 AI객체탐지가 진행중입니다...\n\n 0 / {self.file_count}", "취소", 0, self.file_count, self)
            progress_dialog.setWindowTitle("AI객체탐지 진행 확인창")
            progress_dialog.setWindowModality(Qt.ApplicationModal)
            progress_dialog.setMinimumDuration(0)  # 즉시 표시
            progress_dialog.setValue(0)
            processed_count = 0
            # 파일 처리
            for source in sources:
                # 폴더일 경우 안에 있는 파일을 모두 가져오기
                if os.path.isdir(source):  # 폴더인 경우
                    files_in_folder = [str(file) for file in Path(source).glob("*") if file.is_file()]
                    for file in files_in_folder:
                        self.process_file(model, file, detected_files, output_folder)
                        processed_count += 1
                        progress_dialog.setValue(processed_count)
                        progress_dialog.setLabelText(
                            f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n {processed_count} / {self.file_count}")
                elif os.path.isfile(source):  # 파일인 경우
                    self.process_file(model, source, detected_files, output_folder)
                    processed_count += 1
                    progress_dialog.setValue(processed_count)
                    progress_dialog.setLabelText(
                        f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n {processed_count} / {self.file_count}")
                else:
                    print(f"올바르지 않은 경로: {source}")
                                # 진행률 업데이트


            progress_dialog.close()    
            

            
            end_time = time.time()  # 종료 시간 기록
            execution_time = end_time - start_time  # 실행 시간 계산
            print(f"총 탐지파일 {image_count}장 중 {len(detected_files)}개 객체탐지, 실행 시간: {execution_time} 초")
            # 결과 알림
            self.display_results(image_count, sources, detected_files, folder_status, execution_time)
                        # 예/아니오 확인 메시지 박스
            # 객체가 탐지된 경우에만 GPS 분석 실행
            if len(detected_files) > 0:
                reply = QMessageBox.question(
                    self,
                    "GPS 정보 처리",
                    "GPS 정보 분석을 실행하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # “예” 버튼 클릭 시 실행
                    gps2.process_images_in_folder(output_folder)# gps2.py의 함수 호출
            else:
                print("탐지된 객체가 없어 GPS 분석을 생략합니다.")
            



        elif self.source == '영상':
            source = str(self.juso[0])
            results = model(source, imgsz=self.imgsz, stream=True, save=True, show=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)  # generator of Results objects

            for result in results:
                detected_classes = result.names
                detected_ids = result.boxes.cls

            
            end_time = time.time()  # 종료 시간 기록
            execution_time = end_time - start_time  # 실행 시간 계산
            print(f"실행 시간: {execution_time} 초")


        elif self.source == '외부영상(캡쳐보드)':
            # model.predict(0, stream_buffer=True, show=True, conf=self.percentage, device=self.device) #캡쳐보드
            results = model(0, imgsz=self.imgsz, stream=True, save=False, show=True, conf=self.percentage, device=self.device, classes=self.classes_to_detect)  # generator of Results objects

            for result in results:
                detected_classes = result.names
                detected_ids = result.boxes.cls


            end_time = time.time()  # 종료 시간 기록
            execution_time = end_time - start_time  # 실행 시간 계산
            print(f"실행 시간: {execution_time} 초")    

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