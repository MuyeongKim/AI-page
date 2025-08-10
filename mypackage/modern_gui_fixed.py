# -*- coding: utf-8 -*-

################################################################################
## Modern AI Object Detection GUI - Fixed Version
## Created by: AI Assistant for Stay Up AI Program
## 기존 구조를 유지하면서 모던한 디자인 적용
################################################################################

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QLabel, QPushButton, QComboBox, 
                             QLineEdit, QCheckBox, QFrame, QPlainTextEdit,
                             QApplication, QSizePolicy, QSpacerItem)
from PySide6.QtGui import QFont

class ModernUi_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        
        # 메인 윈도우 설정
        MainWindow.setEnabled(True)
        MainWindow.resize(550, 760)
        MainWindow.setWindowTitle("AI 객체탐지 프로그램 V25.0810 With Stay Up")
        MainWindow.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        
        # 중앙 위젯
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        
        # === 1. 메인 타이틀 ===
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.label.setGeometry(0, 0, 550, 80)
        font_title = QFont()
        font_title.setPointSize(22)
        font_title.setBold(True)
        self.label.setFont(font_title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # === 2. 제작자 정보 ===
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName("label_2")
        self.label_2.setGeometry(430, 75, 91, 31)
        
        # === 3. 영상소스유형 섹션 ===
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName("label_3")
        self.label_3.setGeometry(50, 120, 140, 35)
        font_section = QFont()
        font_section.setPointSize(13)
        self.label_3.setFont(font_section)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.comboBox_source = QComboBox(self.centralwidget)
        self.comboBox_source.addItems([
            "선택하세요", "외부영상(캡쳐보드)", "사진", "영상"
        ])
        self.comboBox_source.setObjectName("comboBox_source")
        self.comboBox_source.setGeometry(190, 125, 210, 32)
        
        # === 4. 객체탐지모델 섹션 ===
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName("label_4")
        self.label_4.setGeometry(50, 185, 140, 35)
        self.label_4.setFont(font_section)
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.comboBox_data = QComboBox(self.centralwidget)
        self.comboBox_data.addItems([
            "선택하세요", "YoloV11_최대(추천)", "YoloV11_대", "YoloV11_중", 
            "YoloV11_소", "YoloV11_최소", "YoloV12(최대)", "YoloV12(최소)",
            "YoloV8(최대)", "VisDrone(예정)", "화염전용탐지(예정)"
        ])
        self.comboBox_data.setObjectName("comboBox_data")
        self.comboBox_data.setGeometry(190, 190, 210, 32)
        
        # === 5. 주소입력창 섹션 ===
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName("label_5")
        self.label_5.setGeometry(50, 250, 140, 35)
        self.label_5.setFont(font_section)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lineEdit_juso = QLineEdit(self.centralwidget)
        self.lineEdit_juso.setObjectName("lineEdit_juso")
        self.lineEdit_juso.setGeometry(200, 255, 180, 32)
        
        self.pushButton_search = QPushButton(self.centralwidget)
        self.pushButton_search.setObjectName("pushButton_search")
        self.pushButton_search.setGeometry(390, 255, 65, 32)
        
        self.pushButton_search_2 = QPushButton(self.centralwidget)
        self.pushButton_search_2.setObjectName("pushButton_search_2")
        self.pushButton_search_2.setGeometry(465, 255, 65, 32)
        
        # === 6. 옵션 설정 섹션 ===
        self.label_7 = QLabel(self.centralwidget)
        self.label_7.setObjectName("label_7")
        self.label_7.setGeometry(50, 315, 140, 35)
        self.label_7.setFont(font_section)
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 옵션 콤보박스들 (소제목과 정렬) - 너비 조정
        self.comboBox_percentage = QComboBox(self.centralwidget)
        self.comboBox_percentage.addItems([
            "신뢰도", "5%", "10%(기본값)", "15%", "20%", "30%", "50%", "80%"
        ])
        self.comboBox_percentage.setObjectName("comboBox_percentage")
        self.comboBox_percentage.setGeometry(190, 320, 100, 32)
        
        self.comboBox_device = QComboBox(self.centralwidget)
        self.comboBox_device.addItems(["사용장치", "CPU", "GPU"])
        self.comboBox_device.setObjectName("comboBox_device")
        self.comboBox_device.setGeometry(300, 320, 90, 32)
        
        self.comboBox_imgsz = QComboBox(self.centralwidget)
        self.comboBox_imgsz.addItems([
            "해상도", "640", "1080", "1280", "1680", "1920(기본값)", "3000", "4000(*)"
        ])
        self.comboBox_imgsz.setObjectName("comboBox_imgsz")
        self.comboBox_imgsz.setGeometry(400, 320, 120, 32)
        
        # 옵션 설명 텍스트 (콤보박스 아래, 일반 텍스트)
        self.label_8 = QLabel(self.centralwidget)
        self.label_8.setObjectName("label_8")
        self.label_8.setGeometry(70, 360, 470, 25)
        font_small = QFont()
        font_small.setPointSize(9)
        self.label_8.setFont(font_small)
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter)
        
        # === 7. 탐지 설정 섹션 === (소제목 오른쪽에 체크박스 배치)
        self.label_10 = QLabel(self.centralwidget)
        self.label_10.setObjectName("label_10")
        self.label_10.setGeometry(50, 400, 140, 35)
        self.label_10.setFont(font_section)
        self.label_10.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.checkBox_person = QCheckBox(self.centralwidget)
        self.checkBox_person.setObjectName("checkBox_person")
        self.checkBox_person.setGeometry(200, 405, 160, 32)
        font_bold = QFont()
        font_bold.setPointSize(12)
        font_bold.setBold(True)
        self.checkBox_person.setFont(font_bold)
        
        self.checkBox_car = QCheckBox(self.centralwidget)
        self.checkBox_car.setObjectName("checkBox_car")
        self.checkBox_car.setGeometry(370, 405, 170, 32)
        self.checkBox_car.setFont(font_bold)
        
        # === 8. 실행/종료 버튼 ===
        self.pushButton_enter = QPushButton(self.centralwidget)
        self.pushButton_enter.setObjectName("pushButton_enter")
        self.pushButton_enter.setGeometry(150, 460, 110, 45)
        self.pushButton_enter.setFont(font_section)
        
        self.pushButton_close = QPushButton(self.centralwidget)
        self.pushButton_close.setObjectName("pushButton_close")
        self.pushButton_close.setGeometry(300, 460, 110, 45)
        self.pushButton_close.setFont(font_section)
        
        # === 9. 사용방법 섹션 ===
        self.label_9 = QLabel(self.centralwidget)
        self.label_9.setObjectName("label_9")
        self.label_9.setGeometry(75, 530, 140, 35)
        self.label_9.setFont(font_section)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.plainTextEdit_2 = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_2.setObjectName("plainTextEdit_2")
        self.plainTextEdit_2.setGeometry(20, 575, 240, 120)
        
        # === 10. 설명창 섹션 ===
        self.label_6 = QLabel(self.centralwidget)
        self.label_6.setObjectName("label_6")
        self.label_6.setGeometry(340, 530, 140, 35)
        self.label_6.setFont(font_section)
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.plainTextEdit = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setGeometry(290, 575, 260, 120)
        
        # === 11. 라이센스 정보 ===
        self.label_11 = QLabel(self.centralwidget)
        self.label_11.setObjectName("label_11")
        self.label_11.setGeometry(80, 710, 391, 16)
        self.label_11.setFont(font_small)
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        
        # === 텍스트 설정 ===
        self.retranslateUi(MainWindow)
        
        # === 모던 스타일 적용 ===
        self.apply_modern_style(MainWindow)

    def retranslateUi(self, MainWindow):
        """UI 텍스트 설정"""
        MainWindow.setWindowTitle("AI 객체탐지 프로그램 V25.0810 With Stay Up")
        
        self.label.setText("AI 객체탐지 실행프로그램")
        self.label_2.setText("제작 : 김무영")
        
        self.label_3.setText("1. 영상소스유형")
        self.label_4.setText("2. 객체탐지모델")
        self.label_5.setText("3. 주소입력창")
        self.label_7.setText("4. 옵션 설정")
        self.label_8.setText("옵션미설정시 기본값 : 신뢰도 10%, 사용장치 GPU, 해상도 1920")
        self.label_10.setText("5. 탐지 설정")
        
        self.pushButton_search.setText("📁 파일")
        self.pushButton_search_2.setText("📂 폴더")
        self.pushButton_enter.setText("🚀 실행하기")
        self.pushButton_close.setText("❌ 종료하기")
        
        self.checkBox_person.setText("👤 \"사람\"만 탐지")
        self.checkBox_car.setText("🚗 \"자동차\"만 탐지")
        
        self.label_9.setText("[사용방법]")
        self.label_6.setText("[설명창]")
        
        self.plainTextEdit_2.setPlainText(
            "1. 영상소스유형에서 외부영상(캡처보드), 사진, 영상 중 1개를 선택한다.\n\n"
            "2. 객체탐지모델은 최대에서 최소까지 5가지이며 최대를 선택하는 것을 추천한다.\n\n"
            "3. 객체탐지를 할 파일 또는 폴더를 선택하면 주소입력창에 입력이 된다.\n\n"
            "4. 옵션값 설정 후 실행하기를 누르면 콘솔창에 실행과정과 결과값이 나타난다."
        )
        
        self.plainTextEdit.setPlainText(
            "#현재 2025년 8월 10일 수정판\n"
            "객체탐지모델 Yolo V11 / V12 추가\n"
            "FPS, 사람, 자동차 탐지갯수 표시 추가\n"
            "모던 GUI 디자인 적용\n\n"
            "※ 실행정지는 실행창에서 Q버튼 입력\n"
            "※ Cuda는 그래픽카드 유무에 따라 사용\n\n\n"
            "[문의]\n"
            "tenmoo@naver.com"
        )
        
        self.label_11.setText("This program utilizes Ultralytics YOLO, licensed under GNU GPL v3.")

    def apply_modern_style(self, MainWindow):
        """모던 스타일시트 적용"""
        style = """
        QMainWindow {
            background-color: #f8f9fa;
            color: #212529;
        }
        
        QWidget {
            background-color: #f8f9fa;
            color: #212529;
            font-family: 'Segoe UI', 'Malgun Gothic', Arial, sans-serif;
        }
        
        QWidget#centralwidget {
            background-color: #f8f9fa;
        }
        
        /* 메인 타이틀 */
        QLabel#label {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            margin: 8px;
            padding: 15px;
        }
        
        /* 제작자 정보 */
        QLabel#label_2 {
            color: #6c757d;
            font-size: 11px;
            font-style: italic;
        }
        
        /* 섹션 제목들 */
        QLabel#label_3, QLabel#label_4, QLabel#label_5, 
        QLabel#label_7, QLabel#label_10, QLabel#label_9, QLabel#label_6 {
            color: white;
            font-weight: bold;
            font-size: 11px;
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 #4facfe, stop:1 #00f2fe);
            border: none;
            border-radius: 12px;
            padding: 8px 12px;
            margin: 3px;
        }
        
        /* 설명 텍스트 */
        QLabel#label_8 {
            color: #495057;
            font-style: normal;
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 8px;
            padding: 5px 10px;
            border: 1px solid rgba(108, 117, 125, 0.2);
        }
        
        QLabel#label_11 {
            color: #6c757d;
            font-style: italic;
        }
        
        /* 콤보박스 스타일 */
        QComboBox {
            padding: 6px 12px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background-color: white;
            font-size: 12px;
            color: #495057;
            selection-background-color: #007bff;
        }
        
        QComboBox:hover {
            border-color: #4facfe;
            background-color: #f8f9fa;
        }
        
        QComboBox:focus {
            border-color: #4facfe;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #dee2e6;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffffff, stop:1 #f8f9fa);
        }
        
        QComboBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 8px solid #6c757d;
            margin-top: 5px;
        }
        
        /* 라인에딧 스타일 */
        QLineEdit {
            padding: 6px 12px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background-color: white;
            font-size: 12px;
            color: #495057;
        }
        
        QLineEdit:hover {
            border-color: #4facfe;
        }
        
        QLineEdit:focus {
            border-color: #4facfe;
            background-color: #fff;
        }
        
        /* 버튼 스타일 */
        QPushButton#pushButton_search, QPushButton#pushButton_search_2 {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #6c757d, stop:1 #5a6268);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: bold;
        }
        
        QPushButton#pushButton_search:hover, QPushButton#pushButton_search_2:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #5a6268, stop:1 #495057);
        }
        
        QPushButton#pushButton_search:pressed, QPushButton#pushButton_search_2:pressed {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #495057, stop:1 #343a40);
        }
        
        QPushButton#pushButton_enter {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #28a745, stop:1 #20c997);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: bold;
        }
        
        QPushButton#pushButton_enter:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #20c997, stop:1 #28a745);
        }
        
        QPushButton#pushButton_close {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #dc3545, stop:1 #fd7e14);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: bold;
        }
        
        QPushButton#pushButton_close:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #fd7e14, stop:1 #dc3545);
        }
        
        /* 체크박스 스타일 */
        QCheckBox {
            font-weight: bold;
            color: #495057;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 3px;
            background-color: white;
        }
        
        QCheckBox::indicator:hover {
            border-color: #007bff;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007bff;
            border-color: #0056b3;
            border: 2px solid #0056b3;
        }
        
        /* 텍스트에딧 스타일 */
        QPlainTextEdit {
            border: 1px solid #dee2e6;
            border-radius: 12px;
            background-color: white;
            font-size: 11px;
            color: #495057;
            padding: 12px;
            line-height: 1.5;
        }
        
        QPlainTextEdit:focus {
            border-color: #4facfe;
        }
        
        /* 스크롤바 스타일 */
        QScrollBar:vertical {
            background-color: #f8f9fa;
            width: 10px;
            border-radius: 5px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background-color: #ced4da;
            border-radius: 5px;
            min-height: 15px;
            margin: 1px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #adb5bd;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        """
        
        MainWindow.setStyleSheet(style)