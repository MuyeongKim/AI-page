# -*- coding: utf-8 -*-

################################################################################
## Modern AI Object Detection GUI - Refined Layout (26.04.09)
## Created by: AI Assistant for Stay Up AI Program
################################################################################

import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ModernUi_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")

        MainWindow.resize(720, 860)
        MainWindow.setMinimumSize(QSize(660, 820))
        MainWindow.setWindowTitle("AI 객체 탐지 프로그램 V26.04.09 With Stay Up")

        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(20, 20, 20, 18)
        self.main_layout.setSpacing(16)

        self._create_widgets()
        self._build_header()
        self._build_settings_card()
        self._build_action_row()
        self._build_info_area()
        self._build_footer()

        self.retranslateUi(MainWindow)
        self.apply_modern_style(MainWindow)

    def _create_widgets(self):
        self.label = QLabel("AI 객체 탐지 프로그램")
        self.label.setObjectName("label")

        self.label_2 = QLabel("제작: 김무영")
        self.label_2.setObjectName("label_2")

        self.label_3 = QLabel("1. 입력 소스")
        self.label_3.setObjectName("label_3")
        self.comboBox_source = QComboBox()
        self.comboBox_source.setObjectName("comboBox_source")
        self.comboBox_source.addItems(
            ["선택하세요", "외부영상(캡처보드)", "사진", "영상"]
        )

        self.label_4 = QLabel("2. 탐지 모델")
        self.label_4.setObjectName("label_4")
        self.comboBox_data = QComboBox()
        self.comboBox_data.setObjectName("comboBox_data")
        self.comboBox_data.addItems(
            [
                "선택하세요",
                "YoloV26_최대(추천)",
                "YoloV26_대",
                "YoloV26_중",
                "YoloV26_소",
                "YoloV26_최소",
                "YoloV11_최대",
                "YoloV11_대",
                "YoloV11_중",
                "YoloV11_소",
                "YoloV11_최소",
                "YoloV12(최대)",
                "YoloV12(최소)",
                "화염전용탐지(예정)",
            ]
        )

        self.label_5 = QLabel("3. 파일 또는 폴더")
        self.label_5.setObjectName("label_5")
        self.lineEdit_juso = QLineEdit()
        self.lineEdit_juso.setObjectName("lineEdit_juso")
        self.lineEdit_juso.setPlaceholderText("탐지할 파일 또는 폴더 경로를 선택하세요")

        self.pushButton_search = QPushButton("파일 선택")
        self.pushButton_search.setObjectName("pushButton_search")
        self.pushButton_search_2 = QPushButton("폴더 선택")
        self.pushButton_search_2.setObjectName("pushButton_search_2")

        self.label_7 = QLabel("4. 실행 옵션")
        self.label_7.setObjectName("label_7")

        self.comboBox_percentage = QComboBox()
        self.comboBox_percentage.setObjectName("comboBox_percentage")
        self.comboBox_percentage.addItems(
            ["신뢰도", "5%", "10%(기본값)", "15%", "20%", "30%", "50%", "80%"]
        )

        self.comboBox_device = QComboBox()
        self.comboBox_device.setObjectName("comboBox_device")
        self.comboBox_device.addItems(["사용장치", "CPU", "GPU"])

        self.comboBox_imgsz = QComboBox()
        self.comboBox_imgsz.setObjectName("comboBox_imgsz")
        self.comboBox_imgsz.addItems(
            ["해상도", "640", "1080", "1280", "1680", "1920(기본값)", "3000", "4000(*)"]
        )

        self.label_8 = QLabel("기본값: 신뢰도 10%, 장치 GPU, 해상도 1920")
        self.label_8.setObjectName("label_8")

        self.label_10 = QLabel("5. 탐지 대상")
        self.label_10.setObjectName("label_10")
        self.checkBox_person = QCheckBox("사람만 탐지")
        self.checkBox_person.setObjectName("checkBox_person")
        self.checkBox_car = QCheckBox("차량만 탐지")
        self.checkBox_car.setObjectName("checkBox_car")

        self.pushButton_enter = QPushButton("탐지 시작")
        self.pushButton_enter.setObjectName("pushButton_enter")
        self.pushButton_close = QPushButton("프로그램 종료")
        self.pushButton_close.setObjectName("pushButton_close")

        self.label_9 = QLabel("사용 방법")
        self.label_9.setObjectName("label_9")
        self.plainTextEdit_2 = QPlainTextEdit()
        self.plainTextEdit_2.setObjectName("plainTextEdit_2")
        self.plainTextEdit_2.setReadOnly(True)
        self.plainTextEdit_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.plainTextEdit_2.setFixedHeight(150)

        self.label_6 = QLabel("프로그램 안내")
        self.label_6.setObjectName("label_6")
        self.plainTextEdit = QPlainTextEdit()
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.plainTextEdit.setFixedHeight(150)

        self.label_11 = QLabel(
            "This program utilizes Ultralytics YOLO, licensed under GNU GPL v3."
        )
        self.label_11.setObjectName("label_11")

    def _build_header(self):
        self.headerCard = QFrame()
        self.headerCard.setObjectName("headerCard")

        header_layout = QVBoxLayout(self.headerCard)
        header_layout.setContentsMargins(24, 22, 24, 20)
        header_layout.setSpacing(8)

        header_top = QHBoxLayout()
        header_top.setContentsMargins(0, 0, 0, 0)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(4)
        title_wrap.addWidget(self.label)

        self.header_subtitle = QLabel(
            "사진, 영상, 외부 입력 소스를 한 화면에서 설정하고 바로 탐지할 수 있습니다."
        )
        self.header_subtitle.setObjectName("header_subtitle")
        self.header_subtitle.setWordWrap(True)
        title_wrap.addWidget(self.header_subtitle)

        header_top.addLayout(title_wrap, 1)
        header_top.addWidget(self.label_2, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        header_layout.addLayout(header_top)
        self.main_layout.addWidget(self.headerCard)

    def _build_settings_card(self):
        self.settings_card = QFrame()
        self.settings_card.setObjectName("settings_card")

        settings_layout = QGridLayout(self.settings_card)
        settings_layout.setContentsMargins(22, 22, 22, 22)
        settings_layout.setHorizontalSpacing(16)
        settings_layout.setVerticalSpacing(18)
        settings_layout.setColumnStretch(1, 1)

        settings_layout.addWidget(self.label_3, 0, 0)
        settings_layout.addWidget(self.comboBox_source, 0, 1)

        settings_layout.addWidget(self.label_4, 1, 0)
        settings_layout.addWidget(self.comboBox_data, 1, 1)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.lineEdit_juso, 1)
        path_row.addWidget(self.pushButton_search)
        path_row.addWidget(self.pushButton_search_2)
        settings_layout.addWidget(self.label_5, 2, 0)
        settings_layout.addLayout(path_row, 2, 1)

        option_row = QHBoxLayout()
        option_row.setSpacing(8)
        option_row.addWidget(self.comboBox_percentage, 1)
        option_row.addWidget(self.comboBox_device, 1)
        option_row.addWidget(self.comboBox_imgsz, 1)
        settings_layout.addWidget(self.label_7, 3, 0)
        settings_layout.addLayout(option_row, 3, 1)

        settings_layout.addWidget(self.label_8, 4, 1)

        detect_row = QHBoxLayout()
        detect_row.setSpacing(18)
        detect_row.addWidget(self.checkBox_person)
        detect_row.addWidget(self.checkBox_car)
        detect_row.addStretch(1)
        settings_layout.addWidget(self.label_10, 5, 0)
        settings_layout.addLayout(detect_row, 5, 1)

        self.main_layout.addWidget(self.settings_card)

    def _build_action_row(self):
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        action_layout.addWidget(self.pushButton_enter, 1)
        action_layout.addWidget(self.pushButton_close, 1)
        self.main_layout.addLayout(action_layout)

    def _build_info_area(self):
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)

        self.infoCardHowTo = QFrame()
        self.infoCardHowTo.setObjectName("infoCard")
        howto_layout = QVBoxLayout(self.infoCardHowTo)
        howto_layout.setContentsMargins(18, 16, 18, 16)
        howto_layout.setSpacing(10)
        howto_layout.addWidget(self.label_9)
        howto_layout.addWidget(self.plainTextEdit_2)

        self.infoCardDesc = QFrame()
        self.infoCardDesc.setObjectName("infoCard")
        desc_layout = QVBoxLayout(self.infoCardDesc)
        desc_layout.setContentsMargins(18, 16, 18, 16)
        desc_layout.setSpacing(10)
        desc_layout.addWidget(self.label_6)
        desc_layout.addWidget(self.plainTextEdit)

        info_layout.addWidget(self.infoCardHowTo, 1)
        info_layout.addWidget(self.infoCardDesc, 1)

        self.main_layout.addLayout(info_layout)

    def _build_footer(self):
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(self.label_11, 0, Qt.AlignmentFlag.AlignCenter)

    def retranslateUi(self, MainWindow):
        self.plainTextEdit_2.setPlainText(
            "1. 입력 소스에서 외부영상, 사진, 영상 중 하나를 선택합니다.\n\n"
            "2. 탐지 모델은 V26 또는 V11 계열 중 목적에 맞는 항목을 선택합니다. "
            "일반적으로는 최대(추천) 모델을 먼저 사용하면 됩니다.\n\n"
            "3. 파일 선택 또는 폴더 선택으로 분석 대상을 지정합니다.\n\n"
            "4. 신뢰도, 장치, 해상도를 조정한 뒤 탐지 시작 버튼을 눌러 실행합니다."
        )

        self.plainTextEdit.setPlainText(
            "버전 V26.04.09\n"
            "- Yolo V26 모델 선택 항목 추가\n"
            "- 모던 GUI 스타일 정리 및 사용자 문구 개선\n"
            "- 결과 표시 흐름과 실행 진입점 보완\n\n"
            "[참고]\n"
            "- 실행 중 중단은 실행 창에서 Q 키로 처리할 수 있습니다.\n"
            "- CUDA 사용 가능 여부에 따라 GPU 또는 CPU가 자동 적용됩니다.\n\n"
            "[문의]\n"
            "tenmoo@naver.com"
        )

    def apply_modern_style(self, MainWindow):
        style = """
        QWidget#centralwidget {
            background: #f4efe7;
            color: #1f2937;
            font-family: 'Malgun Gothic', 'Segoe UI', Arial, sans-serif;
        }

        QFrame#headerCard {
            background: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #0f766e, stop:1 #134e4a
            );
            border-radius: 20px;
        }

        QLabel#label {
            color: #f8fafc;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }

        QLabel#header_subtitle {
            color: rgba(248, 250, 252, 0.88);
            font-size: 13px;
            line-height: 1.45;
        }

        QLabel#label_2 {
            color: rgba(248, 250, 252, 0.78);
            font-size: 11px;
            font-weight: 700;
            padding-top: 4px;
        }

        QFrame#settings_card, QFrame#infoCard {
            background: #fffdf9;
            border: 1px solid #e8dccb;
            border-radius: 18px;
        }

        QLabel#label_3, QLabel#label_4, QLabel#label_5, QLabel#label_7, QLabel#label_10,
        QLabel#label_9, QLabel#label_6 {
            color: #0f3d3a;
            font-size: 13px;
            font-weight: 700;
        }

        QLabel#label_8 {
            color: #6b7280;
            font-size: 11px;
            padding-left: 2px;
        }

        QComboBox, QLineEdit {
            min-height: 42px;
            padding: 0 12px;
            border: 1px solid #d9cbb8;
            border-radius: 12px;
            background: #ffffff;
            color: #1f2937;
            font-size: 12px;
        }

        QComboBox:hover, QLineEdit:hover {
            border-color: #0f766e;
        }

        QComboBox:focus, QLineEdit:focus {
            border: 2px solid #0f766e;
            padding: 0 11px;
        }

        QComboBox::drop-down {
            width: 28px;
            border: none;
        }

        QPushButton#pushButton_search, QPushButton#pushButton_search_2 {
            min-height: 42px;
            padding: 0 16px;
            border: 1px solid #d9cbb8;
            border-radius: 12px;
            background: #efe5d7;
            color: #5b4636;
            font-size: 12px;
            font-weight: 700;
        }

        QPushButton#pushButton_search:hover, QPushButton#pushButton_search_2:hover {
            background: #e5d6c3;
            border-color: #cdb89d;
        }

        QCheckBox {
            color: #374151;
            font-size: 13px;
            font-weight: 700;
            spacing: 8px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 2px solid #cbb79e;
            background: #ffffff;
        }

        QCheckBox::indicator:checked {
            background: #0f766e;
            border-color: #0f766e;
        }

        QPushButton#pushButton_enter, QPushButton#pushButton_close {
            min-height: 52px;
            border-radius: 16px;
            font-size: 15px;
            font-weight: 800;
            padding: 0 18px;
        }

        QPushButton#pushButton_enter {
            background: #0f766e;
            color: #ffffff;
            border: none;
        }

        QPushButton#pushButton_enter:hover {
            background: #115e59;
        }

        QPushButton#pushButton_close {
            background: transparent;
            color: #8b5e3c;
            border: 2px solid #d8c3ad;
        }

        QPushButton#pushButton_close:hover {
            background: #f5eadc;
            border-color: #cda57c;
        }

        QPlainTextEdit {
            border: 1px solid #eadfce;
            border-radius: 12px;
            background: #fffaf4;
            color: #374151;
            font-size: 11px;
            line-height: 1.55;
            padding: 10px;
        }

        QLabel#label_11 {
            color: #8b7b68;
            font-size: 10px;
            padding-top: 4px;
        }

        QScrollBar:vertical {
            background: #f3e8dc;
            width: 10px;
            margin: 4px 0 4px 0;
            border-radius: 5px;
        }

        QScrollBar::handle:vertical {
            background: #cfb59b;
            border-radius: 5px;
            min-height: 24px;
        }

        QScrollBar::handle:vertical:hover {
            background: #ba9c7d;
        }
        """
        MainWindow.setStyleSheet(style)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = ModernUi_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
