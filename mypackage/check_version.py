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

import sys
import requests
from PySide6.QtWidgets import QApplication, QMessageBox

# 현재 버전
CURRENT_VERSION = "25.0810"

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

def show_message(title, message, icon=QMessageBox.Icon.Information):
    """모던한 스타일의 메시지 박스를 띄운다"""
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    
    # 모던한 스타일시트 적용
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #f8f9fa;
            color: #212529;
            font-family: 'Segoe UI', 'Malgun Gothic', Arial, sans-serif;
            font-size: 12px;
        }
        
        QMessageBox QLabel {
            color: #495057;
            font-size: 14px;
            padding: 15px;
            line-height: 1.4;
        }
        
        QMessageBox QPushButton {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #007bff, stop:1 #0056b3);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 25px;
            font-size: 12px;
            font-weight: bold;
            min-width: 90px;
            min-height: 35px;
        }
        
        QMessageBox QPushButton:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #0056b3, stop:1 #007bff);
        }
        
        QMessageBox QPushButton:pressed {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #004085, stop:1 #0056b3);
        }
    """)
    
    msg_box.exec()

def version_to_tuple(version):
    """버전을 숫자 튜플로 변환 (예: '25.0131' → (25, 131))"""
    return tuple(map(int, version.split('.')))

def main():
    """최신 버전을 확인하고 알림을 띄운다"""
    app = QApplication(sys.argv)  # ✅ 여기서 한 번만 생성
    
    print("🔍 AI 객체탐지 프로그램 버전을 확인합니다...")
    latest_version = get_latest_version()
    
    if latest_version == "NO_CONNECTION":
        show_message(
            "🌐 네트워크 연결 오류", 
            "⚠️ 인터넷 연결이 없어 버전 확인을 건너뜁니다.\n\n네트워크 연결 후 다시 시도해주세요.",
            QMessageBox.Icon.Warning
        )
    elif latest_version:
        if version_to_tuple(latest_version) > version_to_tuple(CURRENT_VERSION):
            show_message(
                "🆕 새 버전 발견!", 
                f"<div style='text-align: center; padding: 10px;'>"
                f"<h3 style='color: #28a745; margin: 10px 0;'>🎉 업데이트 가능!</h3>"
                f"<p style='color: #495057; font-size: 14px;'>"
                f"📱 현재 버전: <b>{CURRENT_VERSION}</b><br>"
                f"✨ 최신 버전: <b>{latest_version}</b><br><br>"
                f"🚀 새로운 기능과 개선사항을 경험해보세요!"
                f"</p>"
                f"</div>",
                QMessageBox.Icon.Information
            )
        else:
            show_message(
                "✅ 최신 버전 사용 중", 
                f"<div style='text-align: center; padding: 10px;'>"
                f"<h3 style='color: #007bff; margin: 10px 0;'>🎯 최신 버전!</h3>"
                f"<p style='color: #495057; font-size: 14px;'>"
                f"🚀 현재 버전: <b>{latest_version}</b><br><br>"
                f"✨ 최신 버전을 사용 중입니다!<br>"
                f"🔥 모던 GUI 디자인과 메모리 최적화 적용됨"
                f"</p>"
                f"</div>"
            )
    else:
        show_message(
            "❌ 버전 확인 실패", 
            "🔍 서버에서 최신 버전 정보를 가져올 수 없습니다.\n\n잠시 후 다시 시도해주세요.",
            QMessageBox.Icon.Critical
        )


if __name__ == "__main__":
    main()