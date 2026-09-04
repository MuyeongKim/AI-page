# -*- coding: utf-8 -*-

################################################################################
## Modern AI Object Detection GUI - Refined Layout
## Created by: AI Assistant for Stay Up AI Program
################################################################################

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if __package__:
    from .version import CURRENT_RELEASE, format_gui_changelog
else:  # `python mypackage/modern_gui_fixed.py` direct execution compatibility
    from version import CURRENT_RELEASE, format_gui_changelog


class DeliberateComboBox(QComboBox):
    """Keep page scrolling from silently changing inference settings."""

    def wheelEvent(self, event):
        # An open popup receives wheel events in its own item view. Events on
        # the closed field belong to the surrounding scroll area.
        event.ignore()


class ModernUi_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")

        MainWindow.resize(760, 760)
        MainWindow.setMinimumSize(QSize(560, 560))
        MainWindow.setWindowTitle(CURRENT_RELEASE.window_title)

        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        self.root_layout = QVBoxLayout(self.centralwidget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setObjectName("mainScrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollContent")
        self.main_layout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.main_layout.setContentsMargins(18, 16, 18, 16)
        self.main_layout.setSpacing(14)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.root_layout.addWidget(self.scrollArea)

        self._create_widgets()
        self._build_header()
        self._build_settings_card()
        self._build_info_area()
        self._build_footer()
        self._build_action_row()

        self.retranslateUi(MainWindow)
        self._configure_accessibility(MainWindow)
        self.apply_modern_style(MainWindow)

    def _create_widgets(self):
        self.label = QLabel("AI 객체 탐지 프로그램")
        self.label.setObjectName("label")

        self.label_2 = QLabel("제작: 김무영")
        self.label_2.setObjectName("label_2")

        self.label_3 = QLabel("1. 입력 소스(&S)")
        self.label_3.setObjectName("label_3")
        self.comboBox_source = DeliberateComboBox()
        self.comboBox_source.setObjectName("comboBox_source")
        self.comboBox_source.addItems(["선택하세요", "외부영상(캡처보드)", "사진", "영상"])

        self.label_4 = QLabel("2. 탐지 모델(&M)")
        self.label_4.setObjectName("label_4")
        self.comboBox_data = DeliberateComboBox()
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
        fire_index = self.comboBox_data.findText("화염전용탐지(예정)")
        fire_item = self.comboBox_data.model().item(fire_index)
        if fire_item is not None:
            fire_item.setEnabled(False)
        self.comboBox_data.setItemData(
            fire_index,
            "아직 구현되지 않은 모델입니다. 현재는 선택할 수 없습니다.",
            Qt.ItemDataRole.ToolTipRole,
        )

        self.label_5 = QLabel("3. 파일 또는 폴더(&P)")
        self.label_5.setObjectName("label_5")
        self.lineEdit_juso = QLineEdit()
        self.lineEdit_juso.setObjectName("lineEdit_juso")
        self.lineEdit_juso.setPlaceholderText("탐지할 파일 또는 폴더 경로를 선택하세요")

        self.pushButton_search = QPushButton("파일 선택")
        self.pushButton_search.setObjectName("pushButton_search")
        self.pushButton_search_2 = QPushButton("폴더 선택")
        self.pushButton_search_2.setObjectName("pushButton_search_2")
        self.pushButton_search.setEnabled(False)
        self.pushButton_search_2.setEnabled(False)

        self.label_7 = QLabel("4. 실행 옵션(&O)")
        self.label_7.setObjectName("label_7")

        self.comboBox_percentage = DeliberateComboBox()
        self.comboBox_percentage.setObjectName("comboBox_percentage")
        self.comboBox_percentage.addItems(["5%", "10%(기본값)", "15%", "20%", "30%", "50%", "80%"])
        self.comboBox_percentage.setCurrentText("10%(기본값)")

        self.comboBox_device = DeliberateComboBox()
        self.comboBox_device.setObjectName("comboBox_device")
        self.comboBox_device.addItems(["자동", "CPU", "GPU", "MPS"])
        self.comboBox_device.setCurrentText("자동")

        self.comboBox_imgsz = DeliberateComboBox()
        self.comboBox_imgsz.setObjectName("comboBox_imgsz")
        self.comboBox_imgsz.addItems(
            ["640", "1080", "1280", "1680", "1920(기본값)", "3000", "4000(*)"]
        )
        self.comboBox_imgsz.setCurrentText("1920(기본값)")

        self.label_8 = QLabel("기본값: 신뢰도 10%, 장치 자동(CUDA/MPS/CPU), 해상도 1920")
        self.label_8.setObjectName("label_8")
        self.label_8.setWordWrap(True)
        self.model_hint = QLabel("큰 모델은 더 많은 처리 시간과 메모리가 필요합니다.")
        self.model_hint.setObjectName("model_hint")
        self.model_hint.setWordWrap(True)

        self.label_10 = QLabel("5. 탐지 대상(&T)")
        self.label_10.setObjectName("label_10")
        self.radioButton_all = QRadioButton("전체")
        self.radioButton_all.setObjectName("radioButton_all")
        self.radioButton_person = QRadioButton("사람만")
        self.radioButton_person.setObjectName("radioButton_person")
        self.radioButton_car = QRadioButton("차량만")
        self.radioButton_car.setObjectName("radioButton_car")
        self.pushButton_open_output_folder = QPushButton("탐지 폴더 열기")
        self.pushButton_open_output_folder.setObjectName("pushButton_open_output_folder")
        self.pushButton_open_output_folder.setMinimumWidth(126)
        self.pushButton_open_output_folder.setEnabled(False)
        self.detection_target_group = QButtonGroup()
        self.detection_target_group.setExclusive(True)
        self.detection_target_group.addButton(self.radioButton_all)
        self.detection_target_group.addButton(self.radioButton_person)
        self.detection_target_group.addButton(self.radioButton_car)
        self.radioButton_all.setChecked(True)

        self.pushButton_enter = QPushButton("탐지 시작")
        self.pushButton_enter.setObjectName("pushButton_enter")
        self.pushButton_enter.setEnabled(False)
        self.pushButton_close = QPushButton("프로그램 종료")
        self.pushButton_close.setObjectName("pushButton_close")

        self.status_label = QLabel("준비: 입력 소스와 탐지 모델을 선택해 주세요.")
        self.status_label.setObjectName("status_label")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.label_9 = QLabel("사용 방법")
        self.label_9.setObjectName("label_9")
        self.plainTextEdit_2 = QPlainTextEdit()
        self.plainTextEdit_2.setObjectName("plainTextEdit_2")
        self.plainTextEdit_2.setReadOnly(True)
        self.plainTextEdit_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plainTextEdit_2.setMinimumHeight(150)

        self.label_6 = QLabel("프로그램 안내")
        self.label_6.setObjectName("label_6")
        self.plainTextEdit = QPlainTextEdit()
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plainTextEdit.setMinimumHeight(150)

        self.label_online_notice = QLabel("온라인 소식")
        self.label_online_notice.setObjectName("label_online_notice")
        self.plainTextEdit_online_notice = QTextBrowser()
        self.plainTextEdit_online_notice.setOpenLinks(False)
        self.plainTextEdit_online_notice.setOpenExternalLinks(False)
        self.plainTextEdit_online_notice.setObjectName("plainTextEdit_online_notice")
        self.plainTextEdit_online_notice.setReadOnly(True)
        self.plainTextEdit_online_notice.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.plainTextEdit_online_notice.setMinimumHeight(150)

        self.label_11 = QLabel("This program utilizes Ultralytics YOLO, licensed under AGPL-3.0.")
        self.label_11.setObjectName("label_11")

    def _build_header(self):
        self.headerCard = QFrame()
        self.headerCard.setObjectName("headerCard")

        header_layout = QVBoxLayout(self.headerCard)
        header_layout.setContentsMargins(20, 16, 20, 16)
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
        header_top.addWidget(
            self.label_2,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

        header_layout.addLayout(header_top)
        self.main_layout.addWidget(self.headerCard)

    def _build_settings_card(self):
        self.settings_card = QFrame()
        self.settings_card.setObjectName("settings_card")

        settings_layout = QGridLayout(self.settings_card)
        settings_layout.setContentsMargins(18, 18, 18, 18)
        settings_layout.setHorizontalSpacing(16)
        settings_layout.setVerticalSpacing(12)
        settings_layout.setColumnStretch(1, 1)

        settings_layout.addWidget(self.label_3, 0, 0)
        settings_layout.addWidget(self.comboBox_source, 0, 1)

        settings_layout.addWidget(self.label_4, 1, 0)
        model_column = QVBoxLayout()
        model_column.setSpacing(6)
        model_column.addWidget(self.comboBox_data)
        model_column.addWidget(self.model_hint)
        settings_layout.addLayout(model_column, 1, 1)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.lineEdit_juso, 1)
        path_row.addWidget(self.pushButton_search)
        path_row.addWidget(self.pushButton_search_2)
        settings_layout.addWidget(self.label_5, 2, 0)
        settings_layout.addLayout(path_row, 2, 1)

        option_row = QHBoxLayout()
        option_row.setSpacing(8)
        for title, combo in (
            ("최소 신뢰도", self.comboBox_percentage),
            ("실행 장치", self.comboBox_device),
            ("분석 해상도", self.comboBox_imgsz),
        ):
            column = QVBoxLayout()
            column.setSpacing(6)
            caption = QLabel(title)
            caption.setObjectName("option_caption")
            caption.setBuddy(combo)
            column.addWidget(caption)
            column.addWidget(combo)
            option_row.addLayout(column, 1)
        settings_layout.addWidget(self.label_7, 3, 0)
        settings_layout.addLayout(option_row, 3, 1)

        settings_layout.addWidget(self.label_8, 4, 1)

        detect_row = QHBoxLayout()
        detect_row.setSpacing(8)
        detect_row.addWidget(self.radioButton_all)
        detect_row.addWidget(self.radioButton_person)
        detect_row.addWidget(self.radioButton_car)
        detect_row.addWidget(self.pushButton_open_output_folder)
        detect_row.addStretch(1)

        settings_layout.addWidget(self.label_10, 5, 0, 1, 2)
        settings_layout.addLayout(detect_row, 6, 0, 1, 2)

        self.main_layout.addWidget(self.settings_card)

    def _build_action_row(self):
        self.action_panel = QFrame()
        self.action_panel.setObjectName("action_panel")
        panel_layout = QVBoxLayout(self.action_panel)
        panel_layout.setContentsMargins(18, 10, 18, 12)
        panel_layout.setSpacing(8)
        panel_layout.addWidget(self.status_label)
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        action_layout.addWidget(self.pushButton_enter, 1)
        action_layout.addWidget(self.pushButton_close)
        panel_layout.addLayout(action_layout)
        self.root_layout.addWidget(self.action_panel)

    def _build_info_area(self):
        self.infoTabs = QTabWidget()
        self.infoTabs.setObjectName("infoTabs")
        self.infoTabs.setDocumentMode(True)
        self.infoTabs.setMinimumHeight(230)

        self.resultCard = QFrame()
        self.resultCard.setObjectName("resultCard")
        result_layout = QVBoxLayout(self.resultCard)
        result_layout.setContentsMargins(14, 14, 14, 14)
        self.result_summary = QPlainTextEdit()
        self.result_summary.setReadOnly(True)
        self.result_summary.setMinimumHeight(180)
        self.result_summary.setAccessibleName("마지막 작업 결과와 전체 오류 목록")
        self.result_summary.setPlainText(
            "탐지를 마치면 이곳에 결과와 전체 오류 목록이 남습니다.\n"
            "사진은 원본과 탐지본을 비교하고, 저장 폴더를 바로 열 수 있습니다."
        )
        result_layout.addWidget(self.result_summary)
        self.result_files_combo = DeliberateComboBox()
        self.result_files_combo.setAccessibleName("확인할 결과 파일")
        self.result_files_combo.setEnabled(False)
        result_layout.addWidget(self.result_files_combo)
        result_actions = QHBoxLayout()
        self.open_result_button = QPushButton("결과 열기")
        self.compare_result_button = QPushButton("원본과 비교")
        self.open_output_button = QPushButton("저장 폴더 열기")
        for button in (
            self.open_result_button, self.compare_result_button, self.open_output_button
        ):
            button.setEnabled(False)
            result_actions.addWidget(button)
        result_layout.addLayout(result_actions)

        self.infoCardHowTo = QFrame()
        self.infoCardHowTo.setObjectName("infoCardHowTo")
        howto_layout = QVBoxLayout(self.infoCardHowTo)
        howto_layout.setContentsMargins(18, 16, 18, 16)
        howto_layout.setSpacing(10)
        howto_layout.addWidget(self.label_9)
        howto_layout.addWidget(self.plainTextEdit_2)

        self.infoCardDesc = QFrame()
        self.infoCardDesc.setObjectName("infoCardDesc")
        desc_layout = QVBoxLayout(self.infoCardDesc)
        desc_layout.setContentsMargins(18, 16, 18, 16)
        desc_layout.setSpacing(10)
        desc_layout.addWidget(self.label_6)
        desc_layout.addWidget(self.plainTextEdit)

        self.infoCardOnlineNotice = QFrame()
        self.infoCardOnlineNotice.setObjectName("infoCardOnlineNotice")
        online_notice_layout = QVBoxLayout(self.infoCardOnlineNotice)
        online_notice_layout.setContentsMargins(18, 16, 18, 16)
        online_notice_layout.setSpacing(10)
        online_notice_layout.addWidget(self.label_online_notice)
        online_notice_layout.addWidget(self.plainTextEdit_online_notice)

        self.infoTabs.addTab(self.infoCardHowTo, "사용 방법")
        self.result_tab_index = self.infoTabs.addTab(self.resultCard, "작업 결과")
        self.infoTabs.addTab(self.infoCardDesc, "프로그램 안내")
        self.online_notice_tab_index = self.infoTabs.addTab(
            self.infoCardOnlineNotice, "온라인 소식"
        )
        self.infoTabs.setTabVisible(self.online_notice_tab_index, False)
        self.main_layout.addWidget(self.infoTabs)

    def _build_footer(self):
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(self.label_11, 0, Qt.AlignmentFlag.AlignCenter)

    def retranslateUi(self, MainWindow):
        self.plainTextEdit_2.setPlainText(
            "1. 입력 소스에서 외부영상, 사진, 영상 중 하나를 선택합니다.\n\n"
            "2. 탐지 모델을 선택합니다. 최대 모델은 시간과 메모리를 많이 사용합니다. "
            "처리가 느리면 작은 모델과 낮은 분석 해상도를 직접 선택할 수 있습니다.\n\n"
            "3. 사진/영상은 파일 또는 폴더를 선택하고, "
            "외부영상(캡처보드)은 장치 번호를 입력합니다. "
            "비워두면 0번 장치를 사용합니다.\n\n"
            "4. 최소 신뢰도, 실행 장치, 분석 해상도를 확인하고 탐지 시작을 누릅니다. "
            "신뢰도가 낮으면 후보가 늘지만 오탐도 늘 수 있습니다.\n\n"
            "5. 진행 창에서 단계와 경과시간을 확인합니다. Esc도 취소 요청으로 처리됩니다.\n\n"
            "6. 작업 결과 탭에서 전체 오류·저장 파일을 다시 확인합니다. "
            "사진은 원본과 비교할 수 있습니다. 이 요약은 앱을 종료하면 지워집니다."
        )

        self.plainTextEdit.setPlainText(
            f"{format_gui_changelog()}\n\n"
            "[참고]\n"
            "- 실행 중 중단은 진행 창의 취소 버튼 또는 미리보기 창 닫기로 처리할 수 있습니다.\n"
            "- 자동 장치는 CUDA, Apple MPS, CPU 순서로 선택됩니다.\n"
            "- 탐지 결과는 후보 표시이며 원본과 함께 확인해야 합니다.\n\n"
            "[문의]\n"
            "tenmoo@naver.com"
        )

    def _configure_accessibility(self, MainWindow):
        self.label_3.setBuddy(self.comboBox_source)
        self.label_4.setBuddy(self.comboBox_data)
        self.label_5.setBuddy(self.lineEdit_juso)
        self.label_7.setBuddy(self.comboBox_percentage)
        self.label_10.setBuddy(self.radioButton_all)

        accessibility = (
            (
                self.comboBox_source,
                "입력 소스",
                "사진, 영상, 외부영상 중 분석할 입력 유형을 선택합니다.",
                "먼저 입력 유형을 선택하세요.",
            ),
            (
                self.comboBox_data,
                "탐지 모델",
                "객체 탐지에 사용할 YOLO 모델 크기를 선택합니다.",
                "큰 모델은 정확도가 높을 수 있지만 더 많은 시간과 메모리가 필요합니다.",
            ),
            (
                self.lineEdit_juso,
                "입력 경로 또는 장치 번호",
                "선택한 소스에 맞는 파일, 폴더 경로 또는 캡처 장치 번호를 입력합니다.",
                "사진·영상 경로 또는 외부 입력 장치 번호를 입력하세요.",
            ),
            (
                self.pushButton_search,
                "파일 선택",
                "분석할 사진 또는 영상 파일을 선택합니다.",
                "파일 선택 (Ctrl+O)",
            ),
            (
                self.pushButton_search_2,
                "폴더 선택",
                "분석할 사진 폴더를 선택합니다.",
                "사진이 들어 있는 폴더를 선택합니다.",
            ),
            (
                self.comboBox_percentage,
                "최소 신뢰도",
                "탐지 결과로 인정할 최소 신뢰도입니다.",
                "낮을수록 더 많은 후보를 찾지만 오탐이 늘 수 있습니다.",
            ),
            (
                self.comboBox_device,
                "추론 장치",
                "자동, CPU, GPU 또는 Apple MPS 중 추론 장치를 선택합니다.",
                "자동은 CUDA, MPS, CPU 순서로 사용 가능한 장치를 선택합니다.",
            ),
            (
                self.comboBox_imgsz,
                "추론 해상도",
                "모델에 입력할 영상의 해상도를 선택합니다.",
                "높은 해상도는 더 느리고 메모리를 많이 사용할 수 있습니다. 4000은 고메모리 옵션입니다.",
            ),
            (
                self.radioButton_all,
                "사람과 차량 탐지",
                "사람과 차량을 모두 탐지합니다.",
                "기본 탐지 대상입니다.",
            ),
            (
                self.radioButton_person,
                "사람만 탐지",
                "차량을 제외하고 사람만 탐지합니다.",
                "사람만 탐지합니다.",
            ),
            (
                self.radioButton_car,
                "차량만 탐지",
                "사람을 제외하고 자동차, 버스, 트럭만 탐지합니다.",
                "차량만 탐지합니다.",
            ),
            (
                self.pushButton_open_output_folder,
                "탐지 폴더 열기",
                "마지막으로 완료된 객체 탐지의 결과 폴더를 엽니다.",
                "탐지가 끝나면 결과 폴더를 열 수 있습니다.",
            ),
            (
                self.pushButton_enter,
                "탐지 시작",
                "선택한 설정으로 객체 탐지를 시작합니다.",
                "필수 입력을 마친 뒤 탐지를 시작합니다 (Ctrl+Enter).",
            ),
            (
                self.pushButton_close,
                "프로그램 종료",
                "실행 중인 작업을 안전하게 정리한 뒤 프로그램을 종료합니다.",
                "프로그램을 종료합니다.",
            ),
            (
                self.status_label,
                "작업 상태",
                "입력 준비, 처리 진행 또는 완료 상태를 알려줍니다.",
                "현재 작업 상태를 표시합니다.",
            ),
        )
        for widget, name, description, tooltip in accessibility:
            widget.setAccessibleName(name)
            widget.setAccessibleDescription(description)
            widget.setToolTip(tooltip)

        self.plainTextEdit_2.setAccessibleName("사용 방법")
        self.plainTextEdit.setAccessibleName("프로그램 안내")
        self.plainTextEdit_online_notice.setAccessibleName("온라인 소식 내용")
        self.plainTextEdit_online_notice.setAccessibleDescription(
            "인터넷에서 불러온 공개 공지와 업데이트 소식을 표시합니다."
        )
        self.infoTabs.setAccessibleName("도움말과 프로그램 안내")

        self.open_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Open), MainWindow)
        self.open_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.open_shortcut.activated.connect(self.pushButton_search.click)

        self.start_shortcut = QShortcut(QKeySequence("Ctrl+Return"), MainWindow)
        self.start_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.start_shortcut.activated.connect(self.pushButton_enter.click)

        self.start_enter_shortcut = QShortcut(QKeySequence("Ctrl+Enter"), MainWindow)
        self.start_enter_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.start_enter_shortcut.activated.connect(self.pushButton_enter.click)

    def apply_modern_style(self, MainWindow):
        style = """
        QWidget#centralwidget {
            background: #f4efe7;
            color: #1f2937;
            font-family: 'Malgun Gothic', 'Segoe UI', Arial, sans-serif;
        }

        QScrollArea#mainScrollArea, QWidget#scrollContent {
            background: #f4efe7;
            border: none;
        }

        QFrame#action_panel {
            background: #fffdf9;
            border-top: 1px solid #d9cbb8;
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
            font-size: 25px;
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

        QFrame#settings_card, QFrame#infoCardHowTo, QFrame#infoCardDesc,
        QFrame#infoCardOnlineNotice, QFrame#resultCard {
            background: #fffdf9;
            border: 1px solid #e8dccb;
            border-radius: 18px;
        }

        QLabel#label_3, QLabel#label_4, QLabel#label_5, QLabel#label_7, QLabel#label_10,
        QLabel#label_9, QLabel#label_6, QLabel#label_online_notice {
            color: #0f3d3a;
            font-size: 13px;
            font-weight: 700;
        }

        QLabel#label_8, QLabel#model_hint {
            color: #6b7280;
            font-size: 12px;
            padding-left: 2px;
        }

        QLabel#option_caption {
            color: #374151;
            font-size: 12px;
            font-weight: 600;
        }

        QComboBox, QLineEdit {
            min-height: 42px;
            padding: 0 12px;
            border: 1px solid #d9cbb8;
            border-radius: 12px;
            background: #ffffff;
            color: #1f2937;
            font-size: 13px;
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

        QComboBox::down-arrow {
            image: url("DROPDOWN_ARROW");
            width: 12px;
            height: 8px;
        }

        QPushButton#pushButton_search, QPushButton#pushButton_search_2,
        QPushButton#pushButton_open_output_folder {
            min-height: 42px;
            padding: 0 16px;
            border: 1px solid #d9cbb8;
            border-radius: 12px;
            background: #efe5d7;
            color: #5b4636;
            font-size: 12px;
            font-weight: 700;
        }

        QPushButton#pushButton_search:hover, QPushButton#pushButton_search_2:hover,
        QPushButton#pushButton_open_output_folder:hover {
            background: #e5d6c3;
            border-color: #cdb89d;
        }

        QRadioButton, QCheckBox {
            color: #374151;
            font-size: 13px;
            font-weight: 700;
            spacing: 8px;
            border: 2px solid transparent;
            border-radius: 9px;
            padding: 5px 7px;
        }

        QRadioButton:focus, QCheckBox:focus {
            border: 2px solid #0f766e;
            background: #ecfdf5;
        }

        QRadioButton:disabled, QCheckBox:disabled {
            color: #7c838e;
            background: transparent;
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

        QPushButton#pushButton_search:focus, QPushButton#pushButton_search_2:focus,
        QPushButton#pushButton_open_output_folder:focus {
            border: 2px solid #0f766e;
        }

        QPushButton#pushButton_search:disabled, QPushButton#pushButton_search_2:disabled,
        QPushButton#pushButton_open_output_folder:disabled {
            background: #e5e7eb;
            color: #6b7280;
            border-color: #cbd5e1;
        }

        QPushButton#pushButton_enter, QPushButton#pushButton_close {
            min-height: 52px;
            border-radius: 16px;
            font-size: 15px;
            font-weight: 800;
            padding: 0 18px;
        }

        QFrame#resultCard QPushButton {
            min-height: 38px;
            padding: 0 10px;
            border: 1px solid #c1d2ce;
            border-radius: 8px;
            color: #0f3d3a;
            background: #eef6f3;
            font-size: 12px;
        }

        QFrame#resultCard QPushButton:disabled { color: #6b7280; background: #e5e7eb; }
        QFrame#resultCard QPushButton:focus { border: 2px solid #0f766e; }

        QPushButton#pushButton_enter {
            background: #0f766e;
            color: #ffffff;
            border: none;
        }

        QPushButton#pushButton_enter:hover {
            background: #115e59;
        }

        QPushButton#pushButton_enter:focus {
            border: 3px solid #f59e0b;
        }

        QPushButton#pushButton_enter:disabled {
            background: #9ca3af;
            color: #f8fafc;
            border: 1px solid #87909d;
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

        QPushButton#pushButton_close:focus {
            background: #fff7ed;
            border: 3px solid #9a5b2f;
        }

        QLabel#status_label {
            min-height: 24px;
            padding: 8px 12px;
            border: 1px solid #b7d8d3;
            border-radius: 10px;
            background: #ecfdf5;
            color: #14534d;
            font-size: 12px;
            font-weight: 700;
        }

        QLabel#status_label[state="error"] {
            background: #fff1f2; color: #9f1239; border-color: #fda4af;
        }
        QLabel#status_label[state="warning"] {
            background: #fffbeb; color: #92400e; border-color: #fcd34d;
        }
        QLabel#status_label[state="working"] {
            background: #eff6ff; color: #1e40af; border-color: #bfdbfe;
        }

        QTabWidget#infoTabs::pane {
            border: 1px solid #e8dccb;
            border-radius: 12px;
            background: #fffdf9;
            top: -1px;
        }

        QTabBar::tab {
            min-height: 32px;
            padding: 0 18px;
            margin-right: 4px;
            border: 1px solid #d9cbb8;
            border-bottom: none;
            border-top-left-radius: 9px;
            border-top-right-radius: 9px;
            background: #efe5d7;
            color: #5b4636;
            font-size: 12px;
            font-weight: 700;
        }

        QTabBar::tab:selected {
            background: #fffdf9;
            color: #0f3d3a;
        }

        QTabBar::tab:focus {
            border: 2px solid #0f766e;
        }

        QPlainTextEdit, QTextBrowser {
            border: 1px solid #eadfce;
            border-radius: 12px;
            background: #fffaf4;
            color: #374151;
            font-size: 13px;
            line-height: 1.55;
            padding: 10px;
        }

        QLabel#label_11 {
            color: #5f5549;
            font-size: 12px;
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
        arrow_path = Path(__file__).with_name("icons") / "chevron-down.svg"
        MainWindow.setStyleSheet(style.replace("DROPDOWN_ARROW", arrow_path.as_posix()))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = ModernUi_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
