# AI-page

YOLO와 PySide6 기반의 AI 객체 탐지 프로그램입니다.  
사진, 영상, 외부영상(캡처보드) 입력을 대상으로 사람과 차량을 탐지할 수 있으며, GPS 정보가 포함된 사진은 탐지 후 지도에 표시할 수 있습니다.

## 현재 버전

- `V26.04.09`

## 주요 기능

- PySide6 기반 GUI 실행
- YOLO 모델 선택 지원
  - `YoloV26`
  - `YoloV11`
  - `YoloV12`
- 사진, 영상, 외부영상(캡처보드) 입력 지원
- 사람만 탐지 / 차량만 탐지 옵션
- 탐지 결과 파일을 `detected_files/` 폴더에 저장
- GPS 정보가 포함된 원본 사진 기준으로 지도 생성
- 버전 확인 기능
- 메모리 모니터링 및 정리 로직 포함

## 실행 환경

- Python 3.10 권장
- Windows 환경 기준
- 주요 라이브러리
  - `PySide6`
  - `torch`
  - `torchvision`
  - `ultralytics`
  - `opencv-python`
  - `numpy`
  - `requests`
  - `exifread`
  - `folium`
  - `psutil`

## 실행 방법

```bash
python AI-detection.py
```

## 동작 개요

1. 프로그램 시작
2. 버전 확인
3. GUI 실행
4. 입력 소스와 탐지 모델 선택
5. 파일 또는 폴더 선택
6. 탐지 실행
7. 탐지 결과 저장
8. 필요 시 GPS 지도 생성

## GPS 지도 기능

- `mypackage/gps2.py`에서 GPS 정보가 포함된 사진을 읽어 지도 HTML을 생성합니다.
- 생성된 지도는 브라우저에서 바로 열 수 있도록 로컬 HTTP 서버(`127.0.0.1`)를 통해 표시합니다.
- 이 방식은 `file://` 직접 열기에서 발생할 수 있는 `Referer is required` 문제를 줄이기 위한 처리입니다.

## 주요 파일

```text
AI-page/
├─ AI-detection.py               # 메인 실행 파일
├─ latest_version.json           # 최신 버전 정보
├─ memory_monitor.py             # 메모리 모니터링 도구
├─ memory_optimization_example.py# 메모리 최적화 예시
├─ mypackage/
│  ├─ gui.py                     # 메인 GUI 로직
│  ├─ modern_gui_fixed.py        # 모던 GUI 레이아웃/스타일
│  ├─ start.py                   # 인증 및 시작 로직
│  ├─ check_version.py           # 버전 확인 로직
│  ├─ gps2.py                    # GPS 지도 생성 로직
│  ├─ AI-History.md              # 버전 히스토리
│  └─ modern_gui_fixed.ui        # UI 리소스
└─ detected_files/               # 탐지 결과 저장 폴더
```

## 최근 변경 사항

### 2026.04.09

- 프로그램 버전을 `26.04.09`로 통일
- GUI 문구와 버전 표시 정리
- `Ui_MainWindow.run_app()` 실행 경로 정리
- 결과 표시 후 앱이 다시 시작되던 흐름 수정
- `check_version.py` 네트워크 대기 문제 완화
- GPS 지도 HTML을 로컬 HTTP 서버로 열도록 변경
- 실행창 디자인 및 레이아웃 개선
- 히스토리 문서 갱신

## 참고 사항

- GPU가 없으면 CPU로 자동 전환됩니다.
- 탐지 결과는 입력 종류와 옵션에 따라 처리 시간이 달라질 수 있습니다.
- 지도 기능은 사진 EXIF의 GPS 정보가 있어야 동작합니다.

## 문의

- `tenmoo@naver.com`
