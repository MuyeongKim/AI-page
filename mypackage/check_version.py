import sys
import requests
from PySide6.QtWidgets import QApplication, QMessageBox

# 현재 버전
CURRENT_VERSION = "25.0213"

# 최신 버전 정보 URL
VERSION_INFO_URL = "https://raw.githubusercontent.com/MuyeongKim/AI-page/refs/heads/main/latest_version.json"

def get_latest_version():
    """서버에서 최신 버전 정보를 가져온다"""
    try:
        response = requests.get(VERSION_INFO_URL, timeout=5)
        response.raise_for_status()
        version_info = response.json()
        return version_info.get("version")
    except requests.exceptions.ConnectionError:
        print("인터넷 연결이 없습니다.")
        return "NO_CONNECTION"
    except requests.exceptions.RequestException as e:
        print(f"버전 정보를 가져오는 중 오류 발생: {e}")
        return None

def show_message(title, message):
    """메시지 박스를 띄운다"""
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()

def version_to_tuple(version):
    """버전을 숫자 튜플로 변환 (예: '25.0131' → (25, 131))"""
    return tuple(map(int, version.split('.')))

def main():
    """최신 버전을 확인하고 알림을 띄운다"""
    app = QApplication(sys.argv)  # ✅ 여기서 한 번만 생성
    print("프로그램 버전을 확인합니다.")
    latest_version = get_latest_version()
    
    if latest_version == "NO_CONNECTION":
        show_message("업데이트 오류", "인터넷 연결이 없어 버전 확인을 건너뜁니다.")
    elif latest_version:
        if version_to_tuple(latest_version) > version_to_tuple(CURRENT_VERSION):
            show_message("업데이트 확인", f"현재 버전: {CURRENT_VERSION}\n최신 버전: {latest_version}\n\n업데이트가 필요합니다!")
        else:
            show_message("프로그램 버전 확인", f"최신 버전: {latest_version} <br><br>현재 {latest_version}버전을 사용 중입니다.")
    else:
        show_message("업데이트 오류", "최신 버전 정보를 가져올 수 없습니다.")

if __name__ == "__main__":
    main()
