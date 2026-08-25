# AI-page

YOLO와 PySide6로 구성한 데스크톱 AI 객체 탐지 프로그램입니다.

사진, 영상 파일, 외부영상(캡처보드)에서 사람과 차량을 탐지하고, GPS 정보가 포함된 탐지 사진은 선택적으로 지도에 표시할 수 있습니다.

## 현재 버전

- `V26.08.25`

## 주요 기능

- PySide6 기반 GUI 실행
- YOLO 모델 선택 지원
  - `YoloV26`
  - `YoloV11`
  - `YoloV12`
- 사진, 영상, 외부영상(캡처보드) 입력 지원
- 사람+차량(기본), 사람만, 차량만 중 하나를 선택하는 탐지 필터
- CUDA → Apple MPS → CPU 순서의 자동 장치 선택, 실제 선택값 표시와 수동 지정
- 인증 성공창에서 앱 버전과 자동 감지된 추론 장치 안내
- 탐지 결과를 `detected_files/` 폴더에 저장
  - 사진은 객체가 탐지된 항목만 `original_*`과 `detected_*`로 저장
  - 영상 파일은 입력 재생 끝 도달 여부와 임시 결과의 전체 프레임을 확인한 뒤 `detected_*.mp4`로 전환
  - 외부영상(캡처보드)은 미리보기와 최대 동시 탐지 수 집계만 제공하고 영상을 저장하지 않음
- 완료·부분 완료된 탐지 결과 폴더를 GUI에서 바로 여는 기능
- 완료·부분 완료·실패·취소·외부 영상 연결 끊김 상태를 구분해 표시
- 취소 요청 후 작업 스레드가 종료될 때까지 상태를 표시하고 입력 컨트롤 잠금
- 실시간 미리보기는 최신 프레임 1장만 보관하고 20fps로 표시
- 작은 화면에서도 사용할 수 있는 스크롤 레이아웃과 키보드·스크린리더 보조 정보
- GPS 정보가 포함된 원본 사진 기준으로 지도 생성
- 오프라인에서는 빠르게 건너뛰는 버전 확인 기능
- GitHub의 공지 피드를 비동기로 확인하는 GUI 온라인 소식 영역
- 메모리 모니터링 및 정리 로직 포함

## 실행 환경

- Python 3.10 기준(`pyproject.toml` 정적 검사 대상)
- Windows, macOS, Linux 데스크톱 환경
- 주요 라이브러리
  - `PySide6`
  - `torch`
  - `ultralytics`
  - `opencv-python`
  - `numpy`
  - `requests`
  - `exifread`
  - `folium`
  - `psutil`

## 설치 방법

```bash
python -m venv .venv
```

가상환경을 활성화한 뒤 런타임 의존성을 설치합니다.

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows 명령 프롬프트
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

GPU/CUDA용 PyTorch가 필요하면 사용할 CUDA 버전에 맞는 PyTorch 패키지를 먼저 설치하세요. 모델 가중치(`*.pt`)는 Git에 포함되지 않으며, 프로젝트 루트에 놓거나 Ultralytics가 지원하는 모델 별칭을 통해 받을 수 있습니다. 로컬에 가중치가 없으면 첫 실행 시 외부 네트워크 접속이 필요할 수 있습니다.

실행 인증 키는 `STAYUP_AI_KEY` 환경 변수로 설정할 수 있습니다. 미설정 시에는 코드의 개발용 호환 기본값을 사용합니다. 이 기능은 로컬 편의용 문자열 비교이며 보안 인증·접근 제어 수단이 아닙니다. 운영·배포 환경에서는 반드시 별도의 값을 설정하세요.

```bash
# macOS / Linux
export STAYUP_AI_KEY="별도의-인증-키"

# Windows PowerShell
$env:STAYUP_AI_KEY="별도의-인증-키"
```

## 실행 방법

```bash
python AI-detection.py
```

## 동작 개요

1. 프로그램 시작
2. 버전 확인
3. 인증 키 확인
4. 앱 버전과 자동 감지 장치 확인
5. 감지된 GPU·MPS·CPU 값이 선택된 GUI 실행
6. 입력 소스와 탐지 모델 선택
7. 파일·폴더 또는 캡처 장치 번호 선택
8. 탐지 대상과 실행 옵션 확인 후 탐지 실행
9. 검증된 탐지 결과 저장
10. 필요한 경우에만 GPS 안내를 확인하고 지도 생성

## GPS 지도 기능

- `mypackage/gps2.py`에서 GPS 정보가 포함된 사진을 읽어 지도 HTML을 생성합니다.
- GPS 분석은 이번 탐지 작업에서 복사된 `.jpg`, `.jpeg`, `.png` 원본 파일만 대상으로 합니다.
- 생성된 지도는 브라우저에서 바로 열 수 있도록 로컬 HTTP 서버(`127.0.0.1`)를 통해 표시합니다.
- 로컬 HTTP 서버는 생성된 지도 파일 하나만 제공하며, 같은 폴더의 다른 파일은 제공하지 않습니다.
- 지도 HTML에는 사진의 정확한 GPS 좌표가 저장됩니다. 지도 파일을 공유할 때 위치정보 노출에 주의하세요.
- 지도 표시에는 외부 OpenStreetMap 타일이 사용되므로, 브라우저가 외부 타일 서버에 네트워크 요청을 보냅니다.
- 기본 지도 출력은 Git에서 제외된 `detected_files/` 폴더에 저장되며 기존 파일은 덮어쓰지 않습니다.
- 이 방식은 `file://` 직접 열기에서 발생할 수 있는 `Referer is required` 문제를 줄이기 위한 처리입니다.

## 주요 파일

```text
AI-page/
├─ AI-detection.py               # 메인 실행 파일
├─ LICENSE                       # 프로젝트 AGPL-3.0 라이선스
├─ THIRD_PARTY_NOTICES.md        # 제3자 구성요소 고지
├─ latest_version.json           # 최신 버전 정보
├─ site_updates.json             # 웹·GUI 공용 온라인 공지 형식과 빌드 fallback
├─ scripts/
│  └─ export_release.py          # 로컬 버전에서 공개 릴리스 피드 생성·검증
├─ site/                         # Astro 랜딩페이지·관리자 화면·Vercel API
├─ memory_monitor.py             # 메모리 모니터링 도구
├─ memory_optimization_example.py# 메모리 최적화 예시
├─ mypackage/
│  ├─ gui.py                     # 메인 GUI 로직
│  ├─ modern_gui_fixed.py        # 모던 GUI 레이아웃/스타일
│  ├─ start.py                   # 인증 및 시작 로직
│  ├─ device.py                  # CUDA·Apple MPS·CPU 자동 장치 선택과 안내 문구
│  ├─ version.py                 # 로컬 버전·GUI 변경 이력의 단일 원본
│  ├─ check_version.py           # 버전 확인 로직
│  ├─ notices.py                 # 온라인 공지 조회·검증·로컬 캐시
│  ├─ gps2.py                    # GPS 지도 생성 로직
│  ├─ video_source.py            # 영상·캡처보드 입력 정규화
│  ├─ AI-History.md              # 버전 히스토리
│  └─ modern_gui_fixed.ui        # 보관된 Qt Designer 원본(현재 실행 경로에서는 미사용)
├─ tests/                        # 탐지·GPS·버전·입력 회귀 테스트
└─ detected_files/               # 탐지 결과 저장 폴더(Git 제외)
```

## 최근 변경 사항

### 2026.08.25 `V26.08.25` 시작 환경 자동 설정

- 인증 성공창에 앱 버전과 자동 감지된 추론 장치 결과를 함께 표시
- 사용 가능한 NVIDIA CUDA 장치는 `GPU`, Apple 가속 장치는 `MPS`, 그 외 환경은 `CPU`로 GUI 선택값을 미리 설정
- 단순 하드웨어 존재 여부가 아니라 현재 PyTorch에서 실제 사용할 수 있는 가속 백엔드를 기준으로 안전하게 선택
- 완료·부분 완료된 탐지 작업의 결과 폴더를 GUI에서 바로 여는 버튼 추가
- 인증 키 입력창을 인스턴스 기반 비밀번호 다이얼로그로 변경해 PySide6 호환성 보완

### 2026.08.17 `V26.08.17` 운영 안전성 개선

- 사진 처리 시도·성공·실패 수와 완료·부분 완료·실패·취소 상태 구분
- 컨테이너 보고 프레임 수와 재생 시각을 교차 확인해 조기 종료와 VFR 보고값 차이를 구분
- 실제 처리 프레임 수와 출력 영상 전체 재디코딩 수가 일치할 때만 최종 결과로 저장
- OpenCV 정보만으로 손상 입력과 더 긴 오디오 트랙을 구분할 수 없는 경우, 검증된 영상 결과를 삭제하지 않고 `부분 완료`와 주의 사항으로 보존
- 캡처보드 읽기 종료를 정상 완료가 아닌 입력 연결 끊김으로 표시
- 랜딩페이지 관리자 공지와 GUI 온라인 소식을 GitHub 공통 피드로 연동
- GUI 미리보기를 최신 프레임 1장·20fps 구조로 변경해 프레임 누적 방지
- 버전·창 제목·GUI 변경 이력 단일화와 원격 버전 피드 불일치 테스트 추가

### 2026.08.08 안정성 및 GUI 보완(`V26.08.17`에 포함)

- 사진 탐지 결과를 현재 추론 결과에서 직접 저장하도록 변경해 이전 실행의 동명 파일 재사용 방지
- 영상 결과의 임시 저장, 프레임·디코딩 검증, 원자적 전환, 취소·오류 정리 추가
- 취소 후 스레드 종료까지 진행 상태를 유지하고 실행 중 입력 잠금
- 탐지 대상 라디오 버튼, 실제 기본값 표시, 반응형 스크롤, 접근성·단축키 보완
- GPS 지도의 정확한 좌표 저장·외부 타일 요청 안내, 비정상 EXIF 격리, 생성 지도 Git 제외
- 라이선스·제3자 고지와 결과 무결성 회귀 테스트 추가

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

- 자동 장치는 CUDA, Apple MPS, CPU 순서로 현재 PyTorch에서 실제 사용 가능한지를 확인하고 GUI에 선택 결과를 표시합니다.
- 기본 실행 값은 사람+차량, 신뢰도 10%, 장치 자동, 해상도 1920입니다.
- 탐지 결과는 입력 종류와 옵션에 따라 처리 시간이 달라질 수 있습니다.
- 사진은 `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`를 지원하며, 폴더 선택 시 해당 폴더의 최상위 파일만 처리합니다.
- 영상은 `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.webm`을 지원합니다.
- 영상 파일은 한 번에 하나만 처리하며, 외부영상은 기본적으로 0번 캡처 장치를 사용합니다.
- OpenCV 결과는 무음 CFR MP4로 새로 작성되므로 원본 오디오와 가변 프레임 시각(VFR)은 보존하지 않습니다.
- 캡처보드 동작은 운영체제의 카메라 권한, OpenCV 백엔드, 장치 번호에 의존합니다.
- 실행 중 취소는 현재 추론 단위가 종료된 뒤 반영되는 협력적 취소 방식입니다. 모델 로드·추론 호출 자체가 멈춘 경우를 강제 종료하는 기능은 현재 포함하지 않습니다.
- 인터넷이 연결된 경우 시작 시 GitHub의 `latest_version.json`을 확인하며, 오프라인이면 해당 단계를 건너뜁니다.
- 지도 기능은 사진 EXIF의 GPS 정보가 있어야 동작합니다.

## 개발 및 테스트

개발 도구는 런타임 의존성과 함께 설치됩니다.

```bash
python -m pip install -r requirements-dev.txt
```

전체 테스트와 정적 검사는 다음 명령으로 실행합니다.

```bash
python -m pytest
ruff check .
```

로컬 버전, GUI 창 제목과 GUI 변경 이력은 `mypackage/version.py`에서 함께 관리합니다.
릴리스 전에 실행되는 테스트는 이 정보가 원격 최신 버전 피드인
`latest_version.json`의 버전·릴리스 날짜와 일치하는지도 확인합니다.

공개 릴리스 피드는 다음 명령으로 생성하거나 읽기 전용으로 검증합니다. 새 버전에서는
이전 EXE 링크를 자동으로 폐기하고 Windows 배포본을 `준비 중` 상태로 초기화합니다.

```bash
python scripts/export_release.py
python scripts/export_release.py --check
```

검증된 Windows 배포 파일을 Google Drive에 올린 뒤에는 실제 로컬 파일을 지정해
파일명·크기·SHA-256을 자동 계산하고 다운로드를 활성화합니다.

```bash
python scripts/export_release.py \
  --download-file /path/to/AI-object-detection.exe \
  --download-url https://drive.google.com/file/d/FILE_ID/view
```

공개 전에는 로그아웃 또는 비공개 브라우저에서도 Google Drive 다운로드가 가능한지
확인하고, 내려받은 파일의 SHA-256이 원본과 같은지 별도로 대조해야 합니다.

`site/` 랜딩페이지는 이 피드를 빌드 시 직접 읽으므로 버전·날짜·변경 사항과 Google
Drive 다운로드 상태를 페이지에 다시 입력하지 않습니다. 로컬 사이트 검증은 다음과 같이
실행합니다.

기존 Gamma 공개페이지의 프로그램 화면과 현장 시연 사진은 새 랜딩페이지의 Hero와
`현장 사진` 영역에 선별 보존합니다. 구형 화면은 현재 버전과 혼동되지 않도록 당시 버전을
명시하고, 사진 속 탐지 수치는 성능 보증이 아니라 시연 기록으로 안내합니다.

```bash
cd site
npm ci
npm test
```

일반 공지와 운영 안내는 릴리스 정보와 분리된 `site_updates.json` 계약을 사용합니다.
Vercel의 `/admin`에서 저장하면 GitHub `content` 브랜치에 자동 기록되고, 랜딩페이지와
GUI의 `온라인 소식` 영역이 같은 공개 피드를 비동기로 확인합니다. 조회 실패는 객체 탐지
실행을 막지 않으며 GUI는 마지막 정상 캐시를 사용합니다. 관리자 환경변수와 최초
`content` 브랜치 설정 방법은 [`site/README.md`](site/README.md)를 참고하세요.

디스플레이가 없는 CI 또는 서버에서는 Qt를 offscreen 모드로 실행할 수 있습니다.

```bash
QT_QPA_PLATFORM=offscreen python -m pytest
```

회귀 테스트는 YOLO 모델 추론과 브라우저 실행을 대체 객체로 격리하며, 프로젝트의
`detected_files/` 또는 `runs/` 폴더에 결과 파일을 만들지 않습니다. 실제 모델·코덱·캡처 장치는 환경에 따라 별도 확인이 필요합니다.

## 라이선스

- 프로젝트 라이선스: [GNU AGPL-3.0](LICENSE)
- 주요 제3자 구성요소 고지: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

## 문의

- `tenmoo@naver.com`
