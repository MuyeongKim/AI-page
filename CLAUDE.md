# CLAUDE.md

AI-page 저장소에서 코드를 분석·수정할 때 사용하는 유지보수 지침입니다.

## 언어

- 사용자에게는 항상 한국어로 답변합니다.

## 프로젝트

- PySide6 GUI와 Ultralytics YOLO를 사용하는 데스크톱 객체 탐지 프로그램입니다.
- 사진, 영상 파일, 외부영상(캡처보드)에서 사람과 차량을 탐지합니다.
- 실행 흐름은 `AI-detection.py` → `mypackage/check_version.py` →
  `mypackage/start.py` → `mypackage/gui.py`입니다.
- `mypackage/modern_gui_fixed.py`가 현재 GUI 레이아웃과 스타일을 생성합니다.
- `mypackage/modern_gui_fixed.ui`와 `mypackage/ex_gui.py`는 보관 자료이며 현재
  실행 경로에서 직접 로드하지 않습니다.

## 변경 불변 조건

사용자 확인 없이 다음 정책을 바꾸지 않습니다.

- YOLO 모델 선택 매핑
- 탐지 클래스: 사람 `0`, 차량 `2, 5, 7`
- 기본값: 사람+차량, 신뢰도 10%, 장치 자동, 해상도 1920
- 결과 저장 위치·파일명, 원본 EXIF 보존, 인증 방식, 허용 모델 정책

다음은 탐지 판단을 바꾸는 로직이 아니라 결과 무결성 보장입니다.

- 사진은 `completed`, `partial`, `failed`, `cancelled` 상태와
  시도·성공·실패 수를 구분합니다.
- 영상은 임시 파일에 저장한 뒤 입력 재생 끝 도달 여부와 출력 전체
  프레임을 검증하고 `os.replace()`로 최종 결과를 게시합니다.
- 손상 입력과 더 긴 오디오 트랙을 OpenCV 정보만으로 구분할 수 없으면,
  전체 재검증한 결과를 삭제하지 않고 `partial`과 주의 사항으로 보존합니다.
- 캡처보드의 `read=False`는 사용자 취소가 아니면 `disconnected`입니다.
- 미리보기는 최신 QImage 1장만 보관하고 GUI 스레드가 20fps로 표시합니다.
  탐지와 영상 저장은 미리보기 주기와 무관하게 모든 프레임을 처리합니다.

## 버전 관리

- `mypackage/version.py`는 로컬 버전, GUI 창 제목, GUI 변경 이력의 단일 원본입니다.
- `latest_version.json`은 실행 중 확인하는 원격 최신 버전 피드입니다.
- 버전을 변경할 때 `CURRENT_RELEASE`와 `latest_version.json`을 같이 갱신하고
  `tests/test_version.py`로 버전·릴리스 날짜 일치를 확인합니다.
- 기존 안정성·GUI·GPS 개선 내역을 새 버전 작업에서 삭제하지 않습니다.

## 검증

```bash
python -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q -p no:cacheprovider
ruff check .
git diff --check
```

- 실제 릴리스 전에는 실제 YOLO 사진, 짧은 MP4 생성·전체 재디코딩,
  해당 OS의 캡처보드를 별도로 확인합니다.
- 정책 변경이 필요하면 코드를 먼저 바꾸지 말고 사용자에게 확인합니다.
