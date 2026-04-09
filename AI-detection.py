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
# 업데이트 일자 : 2026.04.09
# 버전 : V26.04.09
#
# 이번 업데이트
# - 프로그램 전반의 버전 표기를 26.04.09로 통일
# - check_version.py와 latest_version.json의 버전 정보 동기화
# - Ui_MainWindow.run_app() 메인 GUI 진입점 복구
# - 결과 표시 후 앱이 다시 시작되던 실행 흐름 수정
# - YOLO26 모델 추가
#
# 이전 주요 업데이트
# - GUI 코드 최종 구성 및 편의 기능 확장
# - 인증창 추가
# - 사람 객체 감지 시 팝업 알림 추가
# - 탐지 파일 별도 폴더 복사 기능 추가
# - 진행률 창 표시 추가
# - 객체 탐지 모델 확장
# - 캡처보드/영상의 사람 전용 탐지 적용
# - 25.01.27: 실시간 선택 시 저장 기능 비활성화, 사람/자동차 선택 기능 추가
# - 25.07.05: 오류 수정, 사람/자동차/FPS 표시 창 추가
# - 25.08.10: 모던 GUI 디자인 적용, Material Design 기반 스타일링
# - 25.08.10 메모리 최적화
#   - 실시간 메모리 모니터링 시스템 추가
#   - FPS 버퍼 O(1) 최적화(deque 사용)
#   - 주기적 메모리 정리 시스템 추가(100프레임마다)
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
        print("🔧 기본 호환 모드로 실행합니다...")
        
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
            print("인증에 실패했습니다.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 기본 GUI를 실행하지 못했습니다: {e}")
        print("💡 PySide6를 최신 버전으로 업데이트해 주세요: pip install --upgrade PySide6")
        sys.exit(1)

def main():
    """메인 실행 함수 - 모던 GUI가 적용된 AI 객체탐지 프로그램"""
    print("🚀 Stay Up AI 객체 탐지 프로그램을 시작합니다.")
    print("🎨 모던 GUI가 적용되었습니다.")
    print("=" * 60)
    
    try:
        # 버전 체크 먼저 실행
        print("📋 버전 확인 중...")
        try:
            check_version.main()
        except KeyboardInterrupt:
            print("⚠️ 버전 확인이 중단되어 이 단계는 건너뜁니다.")
        except Exception as version_error:
            print(f"⚠️ 버전 확인 중 문제가 발생해 이 단계는 건너뜁니다: {version_error}")
        
        print("🖥️  모던 GUI를 불러오는 중...")
        print("✨ 주요 기능:")
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
                print("⚠️  PySide6 호환성 문제를 감지해 기본 GUI로 전환합니다.")
                run_basic_gui()
            else:
                raise attr_error
        
    except ImportError as e:
        print(f"❌ 필요한 모듈을 불러오지 못했습니다: {e}")
        print("💡 설치 확인 방법:")
        print("   1. pip install PySide6 ultralytics opencv-python")
        print("   2. pip install torch torchvision")
        print("   3. 필요한 패키지들이 모두 설치되었는지 확인")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ 프로그램 실행 중 문제가 발생했습니다: {e}")
        print("💡 문의: tenmoo@naver.com")
        sys.exit(1)

if __name__ == "__main__":
    main()
