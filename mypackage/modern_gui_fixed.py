# -*- coding: utf-8 -*-

################################################################################
## Modern AI Object Detection GUI - Layout & Style Refined (25.08.13)
## Created by: AI Assistant for Stay Up AI Program
## ※ 사용자 요청사항 반영: 제목/제작자 정렬, 섹션 박스 높이 조절
################################################################################

import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QGridLayout, QLabel, QPushButton, QComboBox,
                               QLineEdit, QCheckBox, QFrame, QPlainTextEdit,
                               QApplication, QSizePolicy, QSpacerItem)
from PySide6.QtGui import QFont

class ModernUi_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")

        # --- 메인 윈도우 설정 ---
        MainWindow.resize(600, 820)
        MainWindow.setMinimumSize(QSize(580, 780))
        MainWindow.setWindowTitle("AI 객체탐지 프로그램 V25.08.13 With Stay Up")

        # --- 중앙 위젯 및 메인 레이아웃 ---
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- 위젯 생성 (기존 변수명 유지) ---
        self.label = QLabel("AI 객체탐지 실행프로그램")
        self.label.setObjectName("label")
        self.label_2 = QLabel("제작 : 김무영")
        self.label_2.setObjectName("label_2")
        self.label_3 = QLabel("1. 영상소스유형")
        self.label_3.setObjectName("label_3")
        self.comboBox_source = QComboBox()
        self.comboBox_source.addItems(["선택하세요", "외부영상(캡쳐보드)", "사진", "영상"])
        self.comboBox_source.setObjectName("comboBox_source")
        self.label_4 = QLabel("2. 객체탐지모델")
        self.label_4.setObjectName("label_4")
        self.comboBox_data = QComboBox()
        self.comboBox_data.addItems([
            "선택하세요", "YoloV11_최대(추천)", "YoloV11_대", "YoloV11_중",
            "YoloV11_소", "YoloV11_최소", "YoloV12(최대)", "YoloV12(최소)",
            "YoloV8(최대)", "VisDrone(예정)", "화염전용탐지(예정)"
        ])
        self.comboBox_data.setObjectName("comboBox_data")
        self.label_5 = QLabel("3. 주소입력창")
        self.label_5.setObjectName("label_5")
        self.lineEdit_juso = QLineEdit()
        self.lineEdit_juso.setObjectName("lineEdit_juso")
        self.pushButton_search = QPushButton("📁 파일")
        self.pushButton_search.setObjectName("pushButton_search")
        self.pushButton_search_2 = QPushButton("📂 폴더")
        self.pushButton_search_2.setObjectName("pushButton_search_2")
        self.label_7 = QLabel("4. 옵션 설정")
        self.label_7.setObjectName("label_7")
        self.comboBox_percentage = QComboBox()
        self.comboBox_percentage.addItems(["신뢰도", "5%", "10%(기본값)", "15%", "20%", "30%", "50%", "80%"])
        self.comboBox_percentage.setObjectName("comboBox_percentage")
        self.comboBox_device = QComboBox()
        self.comboBox_device.addItems(["사용장치", "CPU", "GPU"])
        self.comboBox_device.setObjectName("comboBox_device")
        self.comboBox_imgsz = QComboBox()
        self.comboBox_imgsz.addItems(["해상도", "640", "1080", "1280", "1680", "1920(기본값)", "3000", "4000(*)"])
        self.comboBox_imgsz.setObjectName("comboBox_imgsz")
        self.label_8 = QLabel("옵션 미설정 시 기본값: 신뢰도 10%, 장치 GPU, 해상도 1920")
        self.label_8.setObjectName("label_8")
        self.label_10 = QLabel("5. 탐지 설정")
        self.label_10.setObjectName("label_10")
        self.checkBox_person = QCheckBox("👤 \"사람\"만 탐지")
        self.checkBox_person.setObjectName("checkBox_person")
        self.checkBox_car = QCheckBox("🚗 \"자동차\"만 탐지")
        self.checkBox_car.setObjectName("checkBox_car")
        self.pushButton_enter = QPushButton("🚀 실행하기")
        self.pushButton_enter.setObjectName("pushButton_enter")
        self.pushButton_close = QPushButton("❌ 종료하기")
        self.pushButton_close.setObjectName("pushButton_close")
        self.label_9 = QLabel("[사용방법]")
        self.label_9.setObjectName("label_9")
        self.plainTextEdit_2 = QPlainTextEdit()
        self.plainTextEdit_2.setObjectName("plainTextEdit_2")
        self.label_6 = QLabel("[설명창]")
        self.label_6.setObjectName("label_6")
        self.plainTextEdit = QPlainTextEdit()
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.label_11 = QLabel("This program utilizes Ultralytics YOLO, licensed under GNU GPL v3.")
        self.label_11.setObjectName("label_11")
        
        # --- 레이아웃에 위젯 배치 ---
        
        # 헤더
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0,0,0,5) # [수정] 아래쪽 여백 추가
        header_layout.setSpacing(5) # [수정] 위젯 간 간격 추가
        
        # [수정] 제목 가운데 정렬
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.label)
        
        # [수정] 제작자 오른쪽 정렬
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.label_2)
        
        self.main_layout.addWidget(header_frame)

        # 설정 섹션 (카드 형식)
        settings_card = QFrame()
        settings_card.setObjectName("settings_card")
        settings_layout = QGridLayout(settings_card)
        settings_layout.setSpacing(18) # [수정] 세로 간격을 늘려 박스를 더 길게 만듦

        # Row 0: 소스 유형
        settings_layout.addWidget(self.label_3, 0, 0)
        settings_layout.addWidget(self.comboBox_source, 0, 1)
        # Row 1: 탐지 모델
        settings_layout.addWidget(self.label_4, 1, 0)
        settings_layout.addWidget(self.comboBox_data, 1, 1)
        # Row 2: 주소 입력
        juso_layout = QHBoxLayout()
        juso_layout.setSpacing(5)
        juso_layout.addWidget(self.lineEdit_juso)
        juso_layout.addWidget(self.pushButton_search)
        juso_layout.addWidget(self.pushButton_search_2)
        settings_layout.addWidget(self.label_5, 2, 0)
        settings_layout.addLayout(juso_layout, 2, 1)
        # Row 3: 옵션 설정
        options_layout = QHBoxLayout()
        options_layout.setSpacing(5)
        options_layout.addWidget(self.comboBox_percentage, 1)
        options_layout.addWidget(self.comboBox_device, 1)
        options_layout.addWidget(self.comboBox_imgsz, 1)
        settings_layout.addWidget(self.label_7, 3, 0)
        settings_layout.addLayout(options_layout, 3, 1)
        # Row 4: 옵션 설명
        settings_layout.addWidget(self.label_8, 4, 1, Qt.AlignmentFlag.AlignCenter)
        # Row 5: 탐지 설정
        detect_layout = QHBoxLayout()
        detect_layout.setSpacing(20)
        detect_layout.addStretch()
        detect_layout.addWidget(self.checkBox_person)
        detect_layout.addWidget(self.checkBox_car)
        detect_layout.addStretch()
        settings_layout.addWidget(self.label_10, 5, 0)
        settings_layout.addLayout(detect_layout, 5, 1)
        
        # [수정] 그리드 레이아웃의 1번 열(입력 위젯)이 늘어나도록 설정
        settings_layout.setColumnStretch(1, 1)
        
        self.main_layout.addWidget(settings_card)

        # 실행/종료 버튼
        run_layout = QHBoxLayout()
        run_layout.addStretch()
        run_layout.addWidget(self.pushButton_enter, 1)
        run_layout.addWidget(self.pushButton_close, 1)
        run_layout.addStretch()
        self.main_layout.addLayout(run_layout)

        # 정보창 (사용방법, 설명)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        how_to_layout = QVBoxLayout()
        how_to_layout.addWidget(self.label_9)
        how_to_layout.addWidget(self.plainTextEdit_2)
        
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(self.label_6)
        desc_layout.addWidget(self.plainTextEdit)
        
        info_layout.addLayout(how_to_layout, 1)
        info_layout.addLayout(desc_layout, 1)
        
        # [수정] 정보창이 무한정 늘어나지 않도록 stretch factor를 0으로 설정
        self.main_layout.addLayout(info_layout, 0)

        # [수정] 하단에 빈 공간을 밀어넣어 위쪽으로 컨텐츠를 정렬
        self.main_layout.addStretch(1)

        # 라이센스
        self.main_layout.addWidget(self.label_11, 0, Qt.AlignmentFlag.AlignCenter)

        # 텍스트 설정 및 스타일 적용
        self.retranslateUi(MainWindow)
        self.apply_modern_style(MainWindow)

    def retranslateUi(self, MainWindow):
        """UI 텍스트 설정 (기존과 동일)"""
        self.plainTextEdit_2.setPlainText(
             "1. 영상소스유형에서 외부영상(캡처보드), 사진, 영상 중 1개를 선택한다.\n\n"
             "2. 객체탐지모델은 최대에서 최소까지 5가지이며 최대를 선택하는 것을 추천한다.\n\n"
             "3. 객체탐지를 할 파일 또는 폴더를 선택하면 주소입력창에 입력이 된다.\n\n"
             "4. 옵션값 설정 후 실행하기를 누르면 콘솔창에 실행과정과 결과값이 나타난다."
        )
        self.plainTextEdit.setPlainText(
             "# 현재 2025년 8월 13일 수정판\n"
             "객체탐지모델 Yolo V11 / V12 추가\n"
             "FPS, 사람, 자동차 탐지갯수 표시 추가\n"
             "모던 반응형 GUI 디자인 적용\n\n"
             "※ 실행정지는 실행창에서 Q버튼 입력\n"
             "※ Cuda는 그래픽카드 유무에 따라 사용\n\n\n"
             "[문의]\n"
             "tenmoo@naver.com"
        )
    
    def apply_modern_style(self, MainWindow):
        """레이아웃에 맞춰 개선된 모던 스타일시트"""
        style = """
        /* 전체 배경 */
        QWidget#centralwidget {
            background-color: #f0f2f5;
            font-family: 'Malgun Gothic', 'Segoe UI', Arial, sans-serif;
        }

        /* 메인 타이틀 라벨 */
        QLabel#label {
            background: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #4e54c8, stop:1 #8f94fb);
            color: white;
            border-radius: 12px;
            font-size: 24px;
            font-weight: bold;
            padding: 20px;
        }
        
        /* [수정] 제작자 정보 라벨 (절대 위치 제거, 일반 스타일 적용) */
        QLabel#label_2 {
            color: #555;
            font-size: 11px;
            font-weight: bold;
            background-color: transparent;
            padding-right: 5px; /* 오른쪽 정렬 시 여백 */
        }
        
        /* 설정 영역 카드 스타일 */
        QFrame#settings_card {
            background-color: white;
            border: 1px solid #e3e3e3;
            border-radius: 12px;
            padding: 20px; /* [수정] 패딩 조정 */
        }

        /* 섹션 제목 라벨들 */
        QLabel#label_3, QLabel#label_4, QLabel#label_5, QLabel#label_7, QLabel#label_10 {
            font-size: 13px;
            font-weight: bold;
            color: #333;
            padding: 5px;
        }
        
        /* 콤보박스, 라인에딧 */
        QComboBox, QLineEdit {
            padding: 8px 10px;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            background-color: #fdfdfd;
            font-size: 12px;
            color: #333;
        }
        QComboBox:hover, QLineEdit:hover { border-color: #8f94fb; }
        QComboBox:focus, QLineEdit:focus { border: 1px solid #4e54c8; }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left: 1px solid #d0d0d0;
        }
        
        /* 파일/폴더 찾기 버튼 */
        QPushButton#pushButton_search, QPushButton#pushButton_search_2 {
            background-color: #6c757d;
            color: white;
            font-weight: bold;
            font-size: 12px;
            border-radius: 6px;
            padding: 8px 10px;
        }
        QPushButton#pushButton_search:hover, QPushButton#pushButton_search_2:hover {
            background-color: #5a6268;
        }
        
        /* 옵션 설명 텍스트 */
        QLabel#label_8 {
            font-size: 11px;
            color: #888;
        }
        
        /* 체크박스 */
        QCheckBox {
            font-size: 13px;
            font-weight: bold;
            color: #444;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px; height: 18px;
            border: 2px solid #ccc;
            border-radius: 4px;
        }
        QCheckBox::indicator:hover { border-color: #8f94fb; }
        QCheckBox::indicator:checked {
            background-color: #4e54c8;
            border-color: #4e54c8;
        }

        /* 실행/종료 버튼 */
        QPushButton#pushButton_enter, QPushButton#pushButton_close {
            font-size: 16px;
            font-weight: bold;
            padding: 12px;
            border-radius: 8px;
        }
        QPushButton#pushButton_enter {
            background: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #11998e, stop:1 #38ef7d);
            color: white;
        }
        QPushButton#pushButton_enter:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #108a7e, stop:1 #32d86d);
        }
        QPushButton#pushButton_close {
            background: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #f46b45, stop:1 #eea849);
            color: white;
        }
        QPushButton#pushButton_close:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #e35a34, stop:1 #d89738);
        }

        /* 정보창 라벨, 텍스트 에디터 */
        QLabel#label_9, QLabel#label_6 {
            font-size: 14px;
            font-weight: bold;
            color: #333;
            margin-left: 5px;
        }
        QPlainTextEdit {
            border: 1px solid #e3e3e3;
            border-radius: 8px;
            background-color: white;
            font-size: 11px;
        }
        
        /* 라이센스 라벨 */
        QLabel#label_11 {
            font-size: 10px;
            color: #aaa;
        }
        
        /* 스크롤바 */
        QScrollBar:vertical {
            background: #f0f2f5; width: 10px;
            margin: 0; border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #d0d0d0; border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover { background: #b0b0b0; }
        """
        MainWindow.setStyleSheet(style)


# 테스트 실행용 코드
if __name__ == '__main__':
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = ModernUi_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())