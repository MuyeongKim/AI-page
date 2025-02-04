import sys
import requests
from PySide6.QtWidgets import QApplication, QMessageBox

# 현재 버전
CURRENT_VERSION = "25.0131"

# 최신 버전 정보 URL (예제)
VERSION_INFO_URL = "https://raw.githubusercontent.com/MuyeongKim/AI-page/refs/heads/main/latest_version.json"

def get_latest_version():
    """서버에서 최신 버전 정보를 가져온다"""
    try:
        response = requests.get(VERSION_INFO_URL, timeout=5)
        response.raise_for_status()
        version_info = response.json()
        return version_info.get("version")
    except Exception as e:
        print(f"버전 정보를 가져오는 중 오류 발생: {e}")
        return None

def show_update_prompt(latest_version):
    """최신 버전이 있으면 메시지 박스를 띄운다"""   
    app = QApplication(sys.argv)  # ✅ 가장 먼저 QApplication 생성
 
    msg_box = QMessageBox()
    msg_box.setWindowTitle("업데이트 확인")
    msg_box.setText(f"현재 버전: {CURRENT_VERSION}\n최신 버전: {latest_version}\n\n업데이트가 필요합니다!")
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()
    
def show_version(latest_version):
    """최신 버전이 있으면 메시지 박스를 띄운다"""    
    app = QApplication(sys.argv)  # ✅ 가장 먼저 QApplication 생성
    msg_box = QMessageBox()
    msg_box.setWindowTitle("프로그램 버전확인")
    msg_box.setText(f"최신 버전: {latest_version}을 사용중입니다.")
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()

def main():
    """최신 버전을 확인하고 알림을 띄운다"""
    
    latest_version = get_latest_version()

    if latest_version and latest_version > CURRENT_VERSION:
        show_update_prompt(latest_version)
        
    else:
        show_version(latest_version)
        
    

if __name__ == "__main__":
    main()