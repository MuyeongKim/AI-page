# 24.12.25 13:35 수정판
# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ex-guiaHnMOc.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QSizePolicy, QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(550, 760)
        MainWindow.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setEnabled(True)
        self.label.setGeometry(QRect(0, 0, 550, 80))
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(430, 70, 91, 31))
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(57, 100, 121, 41))
        font1 = QFont()
        font1.setPointSize(12)
        self.label_3.setFont(font1)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(56, 160, 121, 41))
        self.label_4.setFont(font1)
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(49, 220, 121, 41))
        self.label_5.setFont(font1)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comboBox_source = QComboBox(self.centralwidget)
        self.comboBox_source.addItem("")
        self.comboBox_source.addItem("")
        self.comboBox_source.addItem("")
        self.comboBox_source.addItem("")
        self.comboBox_source.setObjectName(u"comboBox_source")
        self.comboBox_source.setGeometry(QRect(200, 110, 131, 22))
        self.comboBox_data = QComboBox(self.centralwidget)
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.addItem("")
        self.comboBox_data.setObjectName(u"comboBox_data")
        self.comboBox_data.setGeometry(QRect(200, 170, 131, 22))
        self.lineEdit_juso = QLineEdit(self.centralwidget)
        self.lineEdit_juso.setObjectName(u"lineEdit_juso")
        self.lineEdit_juso.setGeometry(QRect(200, 230, 131, 21))
        self.pushButton_search = QPushButton(self.centralwidget)
        self.pushButton_search.setObjectName(u"pushButton_search")
        self.pushButton_search.setGeometry(QRect(340, 230, 51, 24))
        self.pushButton_enter = QPushButton(self.centralwidget)
        self.pushButton_enter.setObjectName(u"pushButton_enter")
        self.pushButton_enter.setGeometry(QRect(140, 390, 101, 41))
        self.pushButton_enter.setFont(font1)
        self.pushButton_close = QPushButton(self.centralwidget)
        self.pushButton_close.setObjectName(u"pushButton_close")
        self.pushButton_close.setGeometry(QRect(300, 390, 101, 41))
        self.pushButton_close.setFont(font1)
        self.label_6 = QLabel(self.centralwidget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(340, 440, 121, 50))
        self.label_6.setFont(font1)
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plainTextEdit = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setGeometry(QRect(280, 490, 251, 211))
        self.label_7 = QLabel(self.centralwidget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(36, 280, 130, 41))
        self.label_7.setFont(font1)
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_8 = QLabel(self.centralwidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(70, 315, 391, 61))
        font2 = QFont()
        font2.setPointSize(8)
        self.label_8.setFont(font2)
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        self.comboBox_percentage = QComboBox(self.centralwidget)
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.addItem("")
        self.comboBox_percentage.setObjectName(u"comboBox_percentage")
        self.comboBox_percentage.setGeometry(QRect(190, 290, 91, 22))
        self.comboBox_device = QComboBox(self.centralwidget)
        self.comboBox_device.addItem("")
        self.comboBox_device.addItem("")
        self.comboBox_device.addItem("")
        self.comboBox_device.setObjectName(u"comboBox_device")
        self.comboBox_device.setGeometry(QRect(280, 290, 91, 22))
        self.comboBox_imgsz = QComboBox(self.centralwidget)
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.addItem("")
        self.comboBox_imgsz.setObjectName(u"comboBox_imgsz")
        self.comboBox_imgsz.setGeometry(QRect(370, 290, 91, 22))
        self.pushButton_search_2 = QPushButton(self.centralwidget)
        self.pushButton_search_2.setObjectName(u"pushButton_search_2")
        self.pushButton_search_2.setGeometry(QRect(390, 230, 51, 24))
        self.label_9 = QLabel(self.centralwidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setGeometry(QRect(80, 440, 110, 50))
        self.label_9.setFont(font1)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plainTextEdit_2 = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_2.setObjectName(u"plainTextEdit_2")
        self.plainTextEdit_2.setGeometry(QRect(20, 490, 231, 211))
        self.checkBox_person = QCheckBox(self.centralwidget)
        self.checkBox_person.setObjectName(u"checkBox_person")
        self.checkBox_person.setGeometry(QRect(190, 344, 131, 31))
        font3 = QFont()
        font3.setPointSize(12)
        font3.setBold(True)
        self.checkBox_person.setFont(font3)
        self.label_10 = QLabel(self.centralwidget)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setGeometry(QRect(37, 340, 130, 41))
        self.label_10.setFont(font1)
        self.label_10.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_11 = QLabel(self.centralwidget)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setGeometry(QRect(160, 720, 391, 16))
        self.label_11.setFont(font2)
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"AI\uac1d\uccb4\ud0d0\uc9c0 \ud504\ub85c\uadf8\ub7a8 V24.1225 With Stay Up", None))
#if QT_CONFIG(tooltip)
        self.label.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\">AI\uac1d\uccb4\ud0d0\uc9c0 \uc2e4\ud589\ud504\ub85c\uadf8\ub7a8</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.label.setText(QCoreApplication.translate("MainWindow", u"AI\uac1d\uccb4\ud0d0\uc9c0 \uc2e4\ud589\ud504\ub85c\uadf8\ub7a8", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"\uc81c\uc791 : \uae40\ubb34\uc601", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"1. \uc601\uc0c1\uc18c\uc2a4\uc720\ud615", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"2. \uac1d\uccb4\ud0d0\uc9c0\ubaa8\ub378", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"3. \uc8fc\uc18c\uc785\ub825\ucc3d", None))
        self.comboBox_source.setItemText(0, QCoreApplication.translate("MainWindow", u"\uc120\ud0dd\ud558\uc138\uc694", None))
        self.comboBox_source.setItemText(1, QCoreApplication.translate("MainWindow", u"\uc678\ubd80\uc601\uc0c1(\ucea1\uccd0\ubcf4\ub4dc)", None))
        self.comboBox_source.setItemText(2, QCoreApplication.translate("MainWindow", u"\uc0ac\uc9c4", None))
        self.comboBox_source.setItemText(3, QCoreApplication.translate("MainWindow", u"\uc601\uc0c1", None))

        self.comboBox_data.setItemText(0, QCoreApplication.translate("MainWindow", u"\uc120\ud0dd\ud558\uc138\uc694", None))
        self.comboBox_data.setItemText(1, QCoreApplication.translate("MainWindow", u"\ucd5c\ub300(\ucd94\ucc9c)", None))
        self.comboBox_data.setItemText(2, QCoreApplication.translate("MainWindow", u"\ub300", None))
        self.comboBox_data.setItemText(3, QCoreApplication.translate("MainWindow", u"\uc911", None))
        self.comboBox_data.setItemText(4, QCoreApplication.translate("MainWindow", u"\uc18c", None))
        self.comboBox_data.setItemText(5, QCoreApplication.translate("MainWindow", u"\ucd5c\uc18c", None))
        self.comboBox_data.setItemText(6, QCoreApplication.translate("MainWindow", u"YoloV8(\ucd5c\ub300)", None))
        self.comboBox_data.setItemText(7, QCoreApplication.translate("MainWindow", u"VisDrone(\uc608\uc815)", None))
        self.comboBox_data.setItemText(8, QCoreApplication.translate("MainWindow", u"\ud654\uc5fc\uc804\uc6a9\ud0d0\uc9c0(\uc608\uc815)", None))

        self.pushButton_search.setText(QCoreApplication.translate("MainWindow", u"\ud30c\uc77c", None))
        self.pushButton_enter.setText(QCoreApplication.translate("MainWindow", u"\uc2e4\ud589\ud558\uae30", None))
        self.pushButton_close.setText(QCoreApplication.translate("MainWindow", u"\uc885\ub8cc\ud558\uae30", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"[\uc124\uba85\ucc3d]", None))
        self.plainTextEdit.setPlainText(QCoreApplication.translate("MainWindow", u"#\ud604\uc7ac 2024\ub144 12\uc6d4 25\uc77c \uc218\uc815\ud310\n"
"\uac1d\uccb4\ud0d0\uc9c0\ubaa8\ub378 Yolo V11 \uc0ac\uc6a9\n"
"\n"
"\u203b \uc2e4\ud589\uc815\uc9c0\ub294 \ucf58\uc194\ucc3d\uc5d0\uc11c Ctrl + C \uc785\ub825\n"
"\u203b Cuda\ub294 \uadf8\ub798\ud53d\uce74\ub4dc \uc720\ubb34\uc5d0 \ub530\ub77c \uc0ac\uc6a9\n"
"\n"
"\n"
"\n"
"\n"
"\n"
"[\ubb38\uc758]\n"
"tenmoo@naver.com", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"4. \uc635\uc158\uc124\uc815", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"\uc635\uc158\ubbf8\uc124\uc815\uc2dc \uae30\ubcf8\uac12 : \uc2e0\ub8b0\ub3c4 10%, \uc0ac\uc6a9\uc7a5\uce58 GPU, \ud574\uc0c1\ub3c4 1920", None))
        self.comboBox_percentage.setItemText(0, QCoreApplication.translate("MainWindow", u"\uc2e0\ub8b0\ub3c4", None))
        self.comboBox_percentage.setItemText(1, QCoreApplication.translate("MainWindow", u"5%", None))
        self.comboBox_percentage.setItemText(2, QCoreApplication.translate("MainWindow", u"10%(\uae30\ubcf8\uac12)", None))
        self.comboBox_percentage.setItemText(3, QCoreApplication.translate("MainWindow", u"15%", None))
        self.comboBox_percentage.setItemText(4, QCoreApplication.translate("MainWindow", u"20%", None))
        self.comboBox_percentage.setItemText(5, QCoreApplication.translate("MainWindow", u"30%", None))
        self.comboBox_percentage.setItemText(6, QCoreApplication.translate("MainWindow", u"50%", None))
        self.comboBox_percentage.setItemText(7, QCoreApplication.translate("MainWindow", u"80%", None))

        self.comboBox_device.setItemText(0, QCoreApplication.translate("MainWindow", u"\uc0ac\uc6a9\uc7a5\uce58", None))
        self.comboBox_device.setItemText(1, QCoreApplication.translate("MainWindow", u"CPU(\uae30\ubcf8\uac12)", None))
        self.comboBox_device.setItemText(2, QCoreApplication.translate("MainWindow", u"CUDA(GPU)", None))

        self.comboBox_imgsz.setItemText(0, QCoreApplication.translate("MainWindow", u"\ud574\uc0c1\ub3c4", None))
        self.comboBox_imgsz.setItemText(1, QCoreApplication.translate("MainWindow", u"640", None))
        self.comboBox_imgsz.setItemText(2, QCoreApplication.translate("MainWindow", u"1080", None))
        self.comboBox_imgsz.setItemText(3, QCoreApplication.translate("MainWindow", u"1280", None))
        self.comboBox_imgsz.setItemText(4, QCoreApplication.translate("MainWindow", u"1680", None))
        self.comboBox_imgsz.setItemText(5, QCoreApplication.translate("MainWindow", u"1920(\uae30\ubcf8\uac12)", None))
        self.comboBox_imgsz.setItemText(6, QCoreApplication.translate("MainWindow", u"3000", None))
        self.comboBox_imgsz.setItemText(7, QCoreApplication.translate("MainWindow", u"4000(*)", None))

        self.pushButton_search_2.setText(QCoreApplication.translate("MainWindow", u"\ud3f4\ub354", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"[\uc0ac\uc6a9\ubc29\ubc95]", None))
        self.plainTextEdit_2.setPlainText(QCoreApplication.translate("MainWindow", u"1. \uc601\uc0c1\uc18c\uc2a4\uc720\ud615\uc5d0\uc11c \uc678\ubd80\uc601\uc0c1(\ucea1\ucc98\ubcf4\ub4dc), \uc0ac\uc9c4, \uc601\uc0c1 \uc911 1\uac1c\ub97c \uc120\ud0dd\ud55c\ub2e4.\n"
"\n"
"2. \uac1d\uccb4\ud0d0\uc9c0\ubaa8\ub378\uc740 \ucd5c\ub300\uc5d0\uc11c \ucd5c\uc18c\uae4c\uc9c0 5\uac00\uc9c0\uc774\uba70 \ucd5c\ub300\ub97c \uc120\ud0dd\ud558\ub294 \uac83\uc744 \ucd94\ucc9c\ud55c\ub2e4.\n"
"\n"
"3. \uac1d\uccb4\ud0d0\uc9c0\ub97c \ud560 \ud30c\uc77c \ub610\ub294 \ud3f4\ub354\ub97c \uc120\ud0dd\ud558\uba74 \uc8fc\uc18c\uc785\ub825\ucc3d\uc5d0 \uc785\ub825\uc774 \ub41c\ub2e4.\n"
"\n"
"4. \uc635\uc158\uac12 \uc124\uc815 \ud6c4 \uc2e4\ud589\ud558\uae30\ub97c \ub204\ub974\uba74 \ucf58\uc194\ucc3d\uc5d0 \uc2e4\ud589\uacfc\uc815\uacfc \uacb0\uacfc\uac12\uc774 \ub098\ud0c0\ub09c\ub2e4.", None))
        self.checkBox_person.setText(QCoreApplication.translate("MainWindow", u"\"\uc0ac\ub78c\"\ub9cc \ud0d0\uc9c0", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"5. \ud0d0\uc9c0\uc124\uc815", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"This program utilizes Ultralytics YOLO, licensed under GNU GPL v3.", None))
    # retranslateUi

