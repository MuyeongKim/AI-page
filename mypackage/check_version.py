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
import socket

import requests
from PySide6.QtWidgets import QApplication, QMessageBox


CURRENT_VERSION = "26.04.09"
VERSION_INFO_URL = "https://raw.githubusercontent.com/MuyeongKim/AI-page/refs/heads/main/latest_version.json"
REQUEST_TIMEOUT = (1.5, 2.5)


def has_internet_connection():
    """빠르게 네트워크 도달 가능 여부를 확인한다."""
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            connection = socket.create_connection((host, port), timeout=0.5)
            connection.close()
            return True
        except OSError:
            continue
    return False


def get_latest_version():
    """서버에서 최신 버전 정보를 가져온다."""
    if not has_internet_connection():
        print("오프라인 상태라 최신 버전 확인을 건너뜁니다.")
        return "NO_CONNECTION"

    try:
        response = requests.get(VERSION_INFO_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        version_info = response.json()
        return version_info.get("version")
    except requests.exceptions.Timeout:
        print("최신 버전 확인 시간이 초과되어 이번 실행에서는 버전 확인을 건너뜁니다.")
        return "TIMEOUT"
    except requests.exceptions.ConnectionError:
        print("인터넷 연결이 없어 최신 버전을 확인하지 못했습니다.")
        return "NO_CONNECTION"
    except requests.exceptions.RequestException as error:
        print(f"최신 버전 정보를 가져오는 중 오류가 발생했습니다: {error}")
        return None


def show_message(title, message, icon=QMessageBox.Icon.Information):
    """메시지 박스를 표시한다."""
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True

    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.setStyleSheet(
        """
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
        """
    )
    msg_box.exec()

    if owns_app:
        app.quit()


def version_to_tuple(version):
    """버전을 숫자 튜플로 변환한다."""
    return tuple(map(int, version.split(".")))


def main():
    """최신 버전을 확인하고 필요할 때만 안내한다."""
    print("버전 정보를 확인하는 중입니다...")
    latest_version = get_latest_version()

    if latest_version in {"TIMEOUT", "NO_CONNECTION", None, ""}:
        return

    if version_to_tuple(latest_version) > version_to_tuple(CURRENT_VERSION):
        show_message(
            "새 버전 안내",
            (
                f"현재 버전: {CURRENT_VERSION}\n"
                f"최신 버전: {latest_version}\n\n"
                "새 버전이 있습니다. 변경 사항을 확인한 뒤 업데이트해 주세요."
            ),
            QMessageBox.Icon.Information,
        )
        return

    show_message(
        "최신 버전 사용 중",
        (
            f"현재 버전: {CURRENT_VERSION}\n\n"
            "현재 최신 버전을 사용 중입니다."
        ),
        QMessageBox.Icon.Information,
    )


if __name__ == "__main__":
    main()
