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
#-----------------------------------------------------------------------------
# 새로고침 일자 : 2025.08.10 
# 수정사항 : 모던 GUI 디자인 적용 + 메모리 최적화
#/////////////////////////////////////////////////////
# 수정사항 : GUI코드 최종 구성 / 편의사항 구성추가예정
# 인증창 추가, 사람 객체감지시 팝업알람 추가 및 별도폴더에 복사기능 추가
# 진행률 창 표시, 객체탐지모델 추가(예정), 캡쳐보드,영상 사람만탐지 적용
# 25.01.27 실시간선택시 저장기능 off, 사람-자동차 선택가능하도록 수정
# 25.07.05 오류수정, 사람,자동차, FPS표시 창 추가
# 25.08.10 모던 GUI 디자인 적용, Material Design 기반 스타일링
# 🚀 25.08.10 메모리 최적화 업데이트:
#   - 실시간 메모리 모니터링 시스템 추가
#   - FPS 버퍼 O(1) 최적화 (deque 사용)
#   - 주기적 메모리 정리 시스템 (100프레임마다)
#   - YOLO 결과 객체 즉시 해제로 메모리 누수 방지
#   - 프로그램 종료 시 메모리 사용량 요약 출력
#-----------------------------------------------------------------------------
import sys
import os
from mypackage import gui
import mypackage.check_version as check_version

def run_basic_gui():
    """기본 GUI 실행 (호환성 문제 해결용)"""
    try:
        print("🔧 기본 호환 모드로 실행 중...")
        
        from mypackage import start
        from PySide6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 기본 인증 시스템 사용
        if start.authenticate():
            # 직접 GUI 클래스 인스턴스화
            window = gui.Ui_MainWindow()
            window.show()
            sys.exit(app.exec())
        else:
            print("인증 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 기본 GUI 실행 실패: {e}")
        print("💡 PySide6 버전을 업데이트해주세요: pip install --upgrade PySide6")
        sys.exit(1)

def main():
    """메인 실행 함수 - 모던 GUI가 적용된 AI 객체탐지 프로그램"""
    print("🚀 Stay Up AI - 객체탐지 프로그램을 시작합니다...")
    print("🎨 새로운 모던 GUI 디자인이 적용되었습니다!")
    print("=" * 60)
    
    try:
        # 버전 체크 먼저 실행
        print("📋 버전 확인 중...")
        check_version.main()
        
        print("🖥️  모던 GUI 로딩 중...")
        print("✨ 새로운 기능들:")
        print("   • Material Design 기반 세련된 인터페이스")
        print("   • 직관적인 아이콘과 버튼")
        print("   • 부드러운 애니메이션 효과")
        print("   • 카드 형태의 섹션 구분")
        print("   • 그라데이션 배경과 그림자 효과")
        print("=" * 60)
        
        # 메인 GUI 애플리케이션 실행
        try:
            gui.Ui_MainWindow.run_app()
        except AttributeError as attr_error:
            if "WindowFlag" in str(attr_error):
                print("⚠️  PySide6 버전 호환성 문제 감지 - 기본 GUI로 전환")
                run_basic_gui()
            else:
                raise attr_error
        
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("💡 해결 방법:")
        print("   1. pip install PySide6 ultralytics opencv-python")
        print("   2. pip install torch torchvision")
        print("   3. 필요한 패키지들이 모두 설치되었는지 확인")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류 발생: {e}")
        print("💡 문의: tenmoo@naver.com")
        sys.exit(1)

if __name__ == "__main__":
    main()
