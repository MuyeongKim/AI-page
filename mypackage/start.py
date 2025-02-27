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


from PySide6.QtWidgets import QMessageBox, QInputDialog
import sys

# 유효기간 및 인증 키 설정
VALID_KEY = "stayup"
MAX_ATTEMPTS = 3  # 최대 인증 시도 횟수

def authenticate():
    # 현재 날짜 확인
    print("프로그램을 실행하고 있습니다")
    

    # 인증 키 입력 받기 (최대 3번 시도)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        user_key, ok = QInputDialog.getText(
            None, "AI객체탐지프로그램 with StayUp", "객체탐지 프로그램 실행을 위한 인증 키를 입력하세요:"
        )
        if ok:
            if user_key == VALID_KEY:
                QMessageBox.information(
                    None, 
                    "성공", 
                    "<p style='text-align: center;'> 인증 성공! <br> AI객체탐지 프로그램을 실행합니다."
                    )
                return True  # 인증 성공
            else:
                attempts += 1
                remaining_attempts = MAX_ATTEMPTS - attempts
                if remaining_attempts > 0:
                    QMessageBox.warning(
                        None,
                        "인증 실패",
                        f"인증 실패! 남은 시도 횟수: {remaining_attempts}회",
                    )
                else:
                    QMessageBox.critical(None, "인증 실패", "인증 실패 횟수 초과! 프로그램을 종료합니다.")
                    sys.exit()  # 프로그램 종료
        else:
            QMessageBox.warning(None, "취소", "인증이 취소되었습니다. 프로그램을 종료합니다.")
            sys.exit()  # 프로그램 종료