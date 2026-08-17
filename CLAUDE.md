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
- 버전을 변경할 때 `CURRENT_RELEASE`를 갱신한 뒤
  `python scripts/export_release.py`로 `latest_version.json`을 생성합니다. 버전·날짜와
  최신 변경 내용을 피드에 다시 수동 입력하지 않습니다.
- `python scripts/export_release.py --check`와 `tests/test_version.py`로 릴리스 정보
  일치를 확인합니다.
- 기존 안정성·GUI·GPS 개선 내역을 새 버전 작업에서 삭제하지 않습니다.

## 랜딩페이지

- `site/`는 Astro 정적 랜딩페이지이며 GitHub–Vercel 배포 대상입니다.
- 사이트의 버전·릴리스 날짜·최신 변경사항·다운로드 상태는 루트
  `latest_version.json`을 빌드 시 읽습니다. 페이지에 같은 내용을 하드코딩하지 않습니다.
- 새 버전을 생성하면 이전 Windows 배포 링크는 자동으로 `preparing` 상태가 됩니다.
- Google Drive 배포본을 공개할 때는 실제 로컬 파일을
  `scripts/export_release.py --download-file ... --download-url ...`에 전달해 파일명,
  크기와 SHA-256을 계산합니다. 공유 링크의 외부 접근성과 내려받은 파일의 SHA-256은
  공개 전에 별도로 확인합니다.
- `SITE_URL`은 실제 Vercel 운영 주소가 확정된 뒤 Production 범위에만 설정합니다.
  기존 `stayup-ai.com`은 다른 서비스가 사용 중이므로 임의로 연결하거나 DNS를 바꾸지 않습니다.
- 루트 `index.html`의 Gamma 이동은 새 Vercel 사이트와 운영 주소를 확인하기 전까지
  제거하지 않습니다.

### 온라인 공지 관리

- `site_updates.json`은 랜딩페이지와 데스크톱 GUI가 함께 읽는 일반 공지 형식과
  빌드 시 fallback입니다. 실제 최신 공지는 GitHub의 `content` 브랜치에만 기록합니다.
- `/admin`의 저장 요청은 Vercel 서버 함수가 검증한 뒤 `content` 브랜치의
  `site_updates.json`만 갱신합니다. 관리자 토큰과 세션 비밀값을 브라우저나 저장소에
  포함하지 않습니다.
- 관리자 화면에서는 일반 공지·릴리스 안내 문구만 관리합니다. 앱 버전, 릴리스 날짜,
  Google Drive 주소, 파일명·크기·SHA-256과 `latest_version.json`은 수정하지 않습니다.
- 온라인 공지 조회 실패는 객체 탐지나 앱 시작을 막지 않아야 하며, GUI는 마지막 정상
  캐시 또는 빈 상태로 안전하게 대체합니다.

## 검증

```bash
python -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q -p no:cacheprovider
ruff check .
git diff --check

cd site
npm ci
npm test
```

- 실제 릴리스 전에는 실제 YOLO 사진, 짧은 MP4 생성·전체 재디코딩,
  해당 OS의 캡처보드를 별도로 확인합니다.
- 정책 변경이 필요하면 코드를 먼저 바꾸지 말고 사용자에게 확인합니다.
