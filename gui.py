#-----------------------------------------------------------------------------
# 새로고침 일자 : 2024.12.2 오후 4시00분
# 수정사항 : GUI코드 최종 구성 / 편의사항 구성추가예정
# 인증창 추가, 사람 객체감지시 팝업알람 추가 및 별도폴더에 복사기능 추가
# 진행률 창 표시, 객체탐지모델 추가(예정), 캡쳐보드,영상 사람만탐지 적용
#-----------------------------------------------------------------------------

import torch
from ex_gui import Ui_MainWindow
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QProgressDialog, QInputDialog
from PySide6.QtCore import Qt
import time
from ultralytics import YOLO
from datetime import datetime
import os
import shutil
import gps2
from PySide6.QtCore import QThread, Signal  # 비동기 처리를 위한 스레드와 시그널



# 유효기간 및 인증 키 설정
EXPIRATION_DATE = datetime(2025, 2, 28)
VALID_KEY = "stayup"
MAX_ATTEMPTS = 3  # 최대 인증 시도 횟수

def authenticate():
    # 현재 날짜 확인
    print("프로그램을 실행하고 있습니다")
    current_date = datetime.now()
    if current_date > EXPIRATION_DATE:
        QMessageBox.critical(None, "오류", "이 프로그램은 2025년 2월 28일 이후에는 실행되지 않습니다.")
        sys.exit()  # 프로그램 종료

    # 인증 키 입력 받기 (최대 3번 시도)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        user_key, ok = QInputDialog.getText(
            None, "AI객체탐지프로그램 with StayUp", "객체탐지 프로그램 실행을 위한 인증 키를 입력하세요:"
        )
        if ok:
            if user_key == VALID_KEY:
                QMessageBox.information(None, "성공", "인증 성공! AI객체탐지 프로그램을 실행합니다.")
                return True  # 인증 성공
            else:
                attempts += 1
                remaining_attempts = MAX_ATTEMPTS - attempts
                if remaining_attempts > 0:
                    QMessageBox.warning(
                        None,
                        "인증 실패",
                        f"인증 실패! 남은 시도 횟수: {remaining_attempts}회",
                    )
                else:
                    QMessageBox.critical(None, "인증 실패", "인증 실패 횟수 초과! 프로그램을 종료합니다.")
                    sys.exit()  # 프로그램 종료
        else:
            QMessageBox.warning(None, "취소", "인증이 취소되었습니다. 프로그램을 종료합니다.")
            sys.exit()  # 프로그램 종료



class Ui_MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Ui_MainWindow, self).__init__()
        self.setupUi(self)
        self.pushButton_close.clicked.connect(self.exit_application) # 종료 버튼 메소드 연결
        self.pushButton_search.clicked.connect(self.browse_files)  # 검색 버튼에 메소드 연결
        self.pushButton_search_2.clicked.connect(self.browse_folders)  # 검색 버튼에 메소드 연결
        self.comboBox_data.currentIndexChanged.connect(self.update_datasize) # 데이터사이즈 선택
        self.comboBox_source.currentIndexChanged.connect(self.update_source) #영상소스 선택
        self.pushButton_enter.clicked.connect(self.submit)  # 검색 버튼에 메소드 연결
        self.lineEdit_juso.textChanged.connect(self.update_juso)  # lineEdit_juso의 textChanged 신호에 함수를 연결
        self.comboBox_percentage.currentIndexChanged.connect(self.option_percentage) # 옵션 임계값 선택
        self.comboBox_device.currentIndexChanged.connect(self.option_device) # 옵션 장치 선택
        self.comboBox_imgsz.currentIndexChanged.connect(self.option_imgsz) # 옵션 장치 선택
        self.checkBox_person.stateChanged.connect(self.update_only_person) # 사람만 탐지 체크박스 선택
        # 초기화
        # 사용자 입력 주소를 저장할 변수
        self.juso = None
        self.percentage = 0.3
        self.device = 'cpu'
        self.imgsz = 1920
        self.buffer = True
        self.only_person = False

    def update_only_person(self, state):
        """체크박스 상태 변경"""
        self.only_person = state == 2  # 체크되면 True, 아니면 False
        print(f"사람만 검색: {self.only_person}")
    
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
            size_dict = {'최대(추천)' : 'yolo11x.pt', '대': 'yolo11l.pt', '중': 'yolo11m.pt', '소': 'yolo11s.pt', '최소': 'yolo11n.pt', 'YoloV8(최대)': 'yolov8x.pt', 'VisDrone(예정)': 'visdrone.pt', '화염전용탐지(예정)' :'fire_detect.py'}
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
        selection = self.comboBox_device.itemText(index)
        
        # GPU/CPU 장치 선택
        if selection == "사용장치":
            self.device = 0  # 기본값 CPU
        else:
            size_dict = {'CPU': 'cpu', 'GPU': 0}
            selected_device = size_dict.get(selection, 'cpu')
            
            # GPU가 없는 경우 자동 전환
            if selected_device == 0 and not torch.cuda.is_available():
                QMessageBox.warning(self, "GPU 사용 불가", "GPU가 없어 CPU로 전환됩니다.")
                selected_device = 'cpu'
            
            self.device = selected_device
        print(f"선택된 장치: {self.device}")


    def option_device(self, index):
        selection = self.comboBox_device.itemText(index)
        if selection == "사용장치":
            self.device = 'cpu'
        else:
            size_dict = {'CPU(기본값)': 'cpu', 'CUDA(GPU)': 0}
            self.device = size_dict[selection]   
        print(self.device)           


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


        

    def submit(self):       
        start_time = time.time()  # 시작 시간 기록

        model = YOLO(self.datasize)
                # 결과를 저장할 변수 초기화
        detected_files = []  # 'person'이 감지된 파일 이름을 저장
        total_people_detected = 0  # 전체 감지된 'person'의 개수
        
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
                        self.process_file(model, file, detected_files, total_people_detected, output_folder)
                        processed_count += 1
                        progress_dialog.setValue(processed_count)
                        progress_dialog.setLabelText(
                            f"사진파일에 대한 AI객체탐지가 진행중입니다...\n\n {processed_count} / {self.file_count}")
                elif os.path.isfile(source):  # 파일인 경우
                    self.process_file(model, source, detected_files, total_people_detected, output_folder)
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
            print(f"총 탐지파일 {image_count}장 중 {len(detected_files)}개 사람탐지, 실행 시간: {execution_time} 초")
            # 결과 알림
            self.display_results(image_count, sources, detected_files, folder_status, execution_time)
            gps2.process_images_in_folder(output_folder)  # gps2.py의 함수 호출
            


        elif self.source == '영상':
            source = str(self.juso[0])
            classes_to_detect = [0] if self.only_person else None  # 'person'만 탐지 또는 전체 탐지
            results = model(source, imgsz=self.imgsz, stream=True, save=True, show=True, conf=self.percentage, device=self.device, classes=classes_to_detect)  # generator of Results objects

            for result in results:
                detected_classes = result.names
                detected_ids = result.boxes.cls

                # 'person' 탐지 결과 계산
                if self.only_person:
                    # '사람만 탐지' 활성화 시, 전체 결과는 이미 'person'만 포함
                    people_count = len(detected_ids)
                else:
                    # 전체 탐지 시, 'person' 클래스 개수 계산
                    people_count = len([cls_id for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person'])

                if people_count > 0:
                    total_people_detected += people_count
                    detected_files.append(source)
                self.people_count = total_people_detected


            end_time = time.time()  # 종료 시간 기록
            execution_time = end_time - start_time  # 실행 시간 계산
            print(f"{self.people_count}명이 {source}에서 탐지되었습니다.")
            print(f"실행 시간: {execution_time} 초")


        elif self.source == '외부영상(캡쳐보드)':
            # model.predict(0, stream_buffer=True, show=True, conf=self.percentage, device=self.device) #캡쳐보드
            classes_to_detect = [0] if self.only_person else None  # 'person'만 탐지 또는 전체 탐지
            results = model(0, imgsz=self.imgsz, stream=True, save=True, show=True, conf=self.percentage, device=self.device, classes=classes_to_detect)  # generator of Results objects

            for result in results:
                detected_classes = result.names
                detected_ids = result.boxes.cls

                # 'person' 탐지 결과 계산
                if self.only_person:
                    # '사람만 탐지' 활성화 시, 전체 결과는 이미 'person'만 포함
                    people_count = len(detected_ids)
                else:
                    # 전체 탐지 시, 'person' 클래스 개수 계산
                    people_count = len([cls_id for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person'])

                if people_count > 0:
                    total_people_detected += people_count
                    detected_files.append(source)
                self.people_count = total_people_detected



            end_time = time.time()  # 종료 시간 기록
            execution_time = end_time - start_time  # 실행 시간 계산
            print(f"{self.people_count}명이 {source}에서 탐지되었습니다.")
            print(f"실행 시간: {execution_time} 초")        


    def process_file(self, model, source, detected_files, total_people_detected, output_folder):
        classes_to_detect = [0] if self.only_person else None  # 'person'만 탐지 또는 전체 탐지

        """단일 파일에 대해 YOLO 모델을 실행하고 원본 및 탐지 결과 파일 복사"""
        results = model(source, stream=True, imgsz=self.imgsz, save=True, show=False, conf=self.percentage, device=self.device, classes=classes_to_detect)

        for result in results:
            detected_classes = result.names
            detected_ids = result.boxes.cls

            # 'person' 탐지 결과 계산
            if self.only_person:
                # '사람만 탐지' 활성화 시, 전체 결과는 이미 'person'만 포함
                people_count = len(detected_ids)
            else:
                # 전체 탐지 시, 'person' 클래스 개수 계산
                people_count = len([cls_id for cls_id in detected_ids if detected_classes[int(cls_id)] == 'person'])

            if people_count > 0:
                print(f"{people_count}명이 {source}에서 탐지되었습니다.")
                total_people_detected += people_count
                detected_files.append(source)

                # 1. 원본 파일 복사
                original_destination = os.path.join(output_folder, "original_" + os.path.basename(source))
                shutil.copy(source, original_destination)

                # 2.   탐지 결과 파일 복사
                result_dir = Path(result.save_dir)  # 현재 결과가 저장된 폴더
                result_file = result_dir / os.path.basename(source)  # 결과 파일 경로

                if result_file.exists():
                    result_destination = os.path.join(output_folder, "detected_" + os.path.basename(source))
                    shutil.copy(result_file, result_destination)
                else:
                    print(f"탐지 결과 파일을 찾을 수 없습니다: {result_file}")





    def display_results(self, image_count, sources, detected_files, folder_status, execution_time):
        """탐지 결과를 팝업 메시지로 표시"""
        if detected_files:
            total_images = image_count if isinstance(self.juso, Path) else len(sources)
            message = (
                f"{folder_status}\n\n"
                f"선택한 사진파일 총 {total_images}장 중 사람이 탐지된 파일 수 : {len(detected_files)}개\n"
                f"탐지된 파일(원본 및 결과파일)은 detected_files 폴더에 저장되었습니다.\n\n"
                f"탐지에 걸린 시간은 {execution_time:.2f}초 입니다."
            )
        else:
            message = (
                f"{folder_status}\n\n"
                f"사진에서 사람이 탐지되지 않았습니다."
            )
        
        QMessageBox.information(
            None, "AI 객체 탐지 완료 with Stay Up", message
        )        

if __name__ == "__main__":        
    app = QApplication(sys.argv)        
    if authenticate():
        window = Ui_MainWindow()
        window.show()
        sys.exit(app.exec())    
    else:
        sys.exit()      # 인증 실패 시 프로그램 종료  