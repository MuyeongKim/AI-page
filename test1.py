from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox, QFileDialog, QWidget


class AIDetectionGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI 객체 탐지 프로그램 V2")
        self.setGeometry(300, 100, 600, 400)
        self.setWindowIcon(QIcon("icon.png"))

        # Main Layout
        main_layout = QVBoxLayout()

        # Program Title
        title_label = QLabel("AI 객체 탐지 실행 프로그램")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Input Group
        input_group = QGroupBox("1. 입력 설정")
        input_layout = QVBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("파일 경로를 입력하세요...")
        browse_button = QPushButton("파일 찾기")
        browse_button.clicked.connect(self.browse_file)

        input_layout.addWidget(QLabel("주소 입력창:"))
        input_layout.addWidget(self.file_path_input)
        input_layout.addWidget(browse_button)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Options Group
        options_group = QGroupBox("2. 옵션 설정")
        options_layout = QVBoxLayout()
        self.model_selector = QComboBox()
        self.model_selector.addItems(["최대(추천)", "중간", "최소"])
        self.gpu_check = QCheckBox("CUDA(GPU) 사용")
        options_layout.addWidget(QLabel("객체 탐지 모델:"))
        options_layout.addWidget(self.model_selector)
        options_layout.addWidget(self.gpu_check)
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Execution Buttons
        exec_layout = QHBoxLayout()
        self.run_button = QPushButton("실행하기")
        self.run_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.stop_button = QPushButton("종료하기")
        self.stop_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        exec_layout.addWidget(self.run_button)
        exec_layout.addWidget(self.stop_button)
        main_layout.addLayout(exec_layout)

        # Footer
        footer = QLabel("This program utilizes Ultralytics YOLO under GNU GPL v3.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size: 10px; color: gray;")
        main_layout.addWidget(footer)

        # Set Layout
        central_widget = QMainWindow()
        central_layout = QVBoxLayout()
        central_layout.addLayout(main_layout)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "이미지 파일 (*.jpg *.png *.bmp)")
        if file_path:
            self.file_path_input.setText(file_path)


if __name__ == "__main__":
    app = QApplication([])
    window = AIDetectionGUI()
    window.show()
    app.exec()
