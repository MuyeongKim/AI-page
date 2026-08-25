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


import os
import sys

from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit, QMessageBox

from mypackage.device import get_preferred_device, get_startup_device_message
from mypackage.version import CURRENT_RELEASE

# 유효기간 및 인증 키 설정
VALID_KEY = os.environ.get("STAYUP_AI_KEY") or "stayup"
MAX_ATTEMPTS = 3  # 최대 인증 시도 횟수

def apply_modern_style():
    """모던한 스타일 적용"""
    app = QApplication.instance()
    if app:
        app.setStyle('Fusion')
        
        # 모던한 스타일시트 적용
        style = """
        QMessageBox {
            background-color: #f8f9fa;
            color: #212529;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }
        
        QMessageBox QLabel {
            color: #495057;
            font-size: 13px;
            padding: 10px;
        }
        
        QMessageBox QPushButton {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #007bff, stop:1 #0056b3);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 11px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QMessageBox QPushButton:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #0056b3, stop:1 #007bff);
        }
        
        QInputDialog {
            background-color: #f8f9fa;
            color: #212529;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        QInputDialog QLineEdit {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            background-color: white;
            font-size: 12px;
            color: #495057;
        }
        
        QInputDialog QLineEdit:focus {
            border-color: #007bff;
        }
        
        QInputDialog QPushButton {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #28a745, stop:1 #20c997);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 11px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QInputDialog QPushButton:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #20c997, stop:1 #28a745);
        }
        """
        app.setStyleSheet(style)


def _prompt_for_key(title, label):
    """Prompt for an authentication key without the unstable static Qt overload."""
    dialog = QInputDialog()
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return dialog.textValue(), accepted


def build_authentication_success_message(device):
    """인증 성공, 앱 버전, 자동 장치 설정 결과를 하나의 안내로 만든다."""
    return "\n".join(
        (
            "인증 성공!",
            f"Stay Up AI {CURRENT_RELEASE.display_version}를 실행합니다.",
            get_startup_device_message(device),
        )
    )

def authenticate_basic():
    """기본 인증 시스템 (호환성용)"""
    print("🚀 Stay Up AI - 프로그램을 시작합니다...")
    print("🔐 기본 인증 시스템 로딩 중...")
    
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        user_key, ok = _prompt_for_key(
            "Stay Up AI - 인증",
            "AI 객체탐지 프로그램 실행을 위한 인증 키를 입력하세요:",
        )
        
        if ok and user_key:
            if user_key == VALID_KEY:
                selected_device = get_preferred_device()
                QMessageBox.information(
                    None,
                    "인증 성공",
                    build_authentication_success_message(selected_device),
                )
                return True
            else:
                attempts += 1
                remaining_attempts = MAX_ATTEMPTS - attempts
                if remaining_attempts > 0:
                    QMessageBox.warning(
                        None,
                        "인증 실패",
                        f"인증 실패!\n남은 시도 횟수: {remaining_attempts}회",
                    )
                else:
                    QMessageBox.critical(
                        None,
                        "인증 실패",
                        "인증 실패 횟수 초과!\n프로그램을 종료합니다.",
                    )
                    sys.exit()
        else:
            QMessageBox.warning(None, "취소", "인증이 취소되었습니다.\n프로그램을 종료합니다.")
            sys.exit()

def authenticate():
    """모던한 스타일의 인증 시스템"""
    try:
        # 모던 스타일 적용
        apply_modern_style()
        
        print("🚀 Stay Up AI - 프로그램을 시작합니다...")
        print("🔐 인증 시스템 로딩 중...")
    except Exception as e:
        print(f"⚠️ 모던 스타일 적용 실패, 기본 모드로 전환: {e}")
        return authenticate_basic()
    
    # 인증 키 입력 받기 (최대 3번 시도)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        # 모던한 입력 다이얼로그
        user_key, ok = _prompt_for_key(
            "🔐 Stay Up AI - 인증",
            "✨ AI 객체탐지 프로그램 실행을 위한 인증 키를 입력하세요:\n\n🔑 인증 키:",
        )
        
        if ok and user_key:
            if user_key == VALID_KEY:
                selected_device = get_preferred_device()
                # 성공 메시지
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("✅ 인증 성공")
                msg.setText(
                    "<div style='text-align: center; padding: 10px;'>"
                    "<h3 style='color: #28a745; margin: 10px 0;'>🎉 인증 성공!</h3>"
                    f"<p style='color: #495057; font-size: 13px;'>"
                    f"Stay Up AI {CURRENT_RELEASE.display_version}를 실행합니다.<br>"
                    f"{get_startup_device_message(selected_device)}"
                    "</p>"
                    "</div>"
                )
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()
                return True  # 인증 성공
            else:
                attempts += 1
                remaining_attempts = MAX_ATTEMPTS - attempts
                if remaining_attempts > 0:
                    # 실패 메시지
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle("⚠️ 인증 실패")
                    msg.setText(
                        "<div style='text-align: center; padding: 10px;'>"
                        "<h3 style='color: #dc3545; margin: 10px 0;'>❌ 인증 실패!</h3>"
                        "<p style='color: #495057; font-size: 13px;'>"
                        f"올바른 인증 키를 입력해주세요.<br>"
                        f"💫 남은 시도 횟수: <b>{remaining_attempts}회</b>"
                        "</p>"
                        "</div>"
                    )
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()
                else:
                    # 최종 실패 메시지
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("🚫 접근 차단")
                    msg.setText(
                        "<div style='text-align: center; padding: 10px;'>"
                        "<h3 style='color: #dc3545; margin: 10px 0;'>🚫 접근 차단</h3>"
                        "<p style='color: #495057; font-size: 13px;'>"
                        "인증 실패 횟수를 초과했습니다.<br>"
                        "프로그램을 종료합니다."
                        "</p>"
                        "</div>"
                    )
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.exec()
                    sys.exit()
        else:
            # 취소 메시지
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("ℹ️ 인증 취소")
            msg.setText(
                "<div style='text-align: center; padding: 10px;'>"
                "<h3 style='color: #6c757d; margin: 10px 0;'>ℹ️ 인증이 취소되었습니다</h3>"
                "<p style='color: #495057; font-size: 13px;'>"
                "프로그램을 종료합니다.<br>"
                "다시 실행해주세요."
                "</p>"
                "</div>"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            sys.exit()

def main():
    """메인 실행 함수"""
    app = QApplication(sys.argv)
    
    if authenticate():
        # gui.py에서 Ui_MainWindow 클래스를 가져와서 실행
        from mypackage.gui import Ui_MainWindow
        window = Ui_MainWindow()
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
