from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QLineEdit, QWidget, QCheckBox, QGroupBox, QTabWidget, QFrame
)
from PySide6.QtCore import Qt


class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern AI Detection GUI")
        self.resize(800, 600)

        # Central Widget
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)

        # Main Layout
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title Section
        title_frame = QFrame()
        title_layout = QVBoxLayout(title_frame)
        title_layout.setSpacing(10)
        self.title_label = QLabel("AI Detection Program")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        self.subtitle_label = QLabel("Enhancing Object Detection with Modern Design")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        main_layout.addWidget(title_frame)

        # Tab Section
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("font-size: 14px; background-color: #ecf0f1;")
        main_layout.addWidget(self.tab_widget)

        # Tab 1: Configuration
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)

        # Source Group
        source_group = QGroupBox("Source Settings")
        source_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        source_layout = QVBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Select Source", "External Video", "Image", "Video"])
        source_layout.addWidget(QLabel("Choose Source Type:"))
        source_layout.addWidget(self.source_combo)
        source_group.setLayout(source_layout)
        config_layout.addWidget(source_group)

        # Options Group
        options_group = QGroupBox("Detection Options")
        options_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        options_layout = QVBoxLayout()
        self.person_checkbox = QCheckBox("Detect 'Person' Only")
        self.person_checkbox.setStyleSheet("font-size: 14px;")
        options_layout.addWidget(self.person_checkbox)
        options_group.setLayout(options_layout)
        config_layout.addWidget(options_group)

        # File Input
        file_input_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Enter file path or browse")
        self.file_input.setStyleSheet("font-size: 14px; padding: 5px;")
        self.browse_button = QPushButton("Browse")
        self.browse_button.setStyleSheet(
            "font-size: 14px; padding: 5px; background-color: #3498db; color: white; border-radius: 5px;"
        )
        file_input_layout.addWidget(self.file_input)
        file_input_layout.addWidget(self.browse_button)
        config_layout.addLayout(file_input_layout)

        self.tab_widget.addTab(config_tab, "Configuration")

        # Tab 2: Status
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)

        self.status_label = QLabel("Status: Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; color: #2ecc71;")
        status_layout.addWidget(self.status_label)

        self.tab_widget.addTab(status_tab, "Status")

        # Action Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 10px; background-color: #27ae60; color: white; border-radius: 5px;"
        )
        self.exit_button = QPushButton("Exit")
        self.exit_button.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 10px; background-color: #e74c3c; color: white; border-radius: 5px;"
        )
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.exit_button)
        main_layout.addLayout(button_layout)


# Run Application
if __name__ == "__main__":
    app = QApplication([])
    window = ModernMainWindow()
    window.show()
    app.exec()

