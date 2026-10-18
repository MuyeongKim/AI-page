# 사용설명서 관리

- 편집 원본: `docs/사용설명서.md`
- PDF: `output/pdf/Stay-Up-AI-사용설명서-V26.1018.pdf`
- 생성기: `scripts/build_user_manual.py`
- 기준: `mypackage/version.py`의 V26.1018, 2026-10-18 개정
- 화면: `docs/images/manual-main-V26.1018.png`. 현재 소스 GUI를 `scripts/capture_user_manual.py`로 캡처한다. 이번 화면은 macOS 개발 환경의 실제 위젯 렌더링이며 Windows 인수시험 화면으로 표기하지 않는다. 웹사이트도 같은 이미지와 PDF 원본을 사용한다.

Markdown의 `<!-- pagebreak -->`는 PDF의 고정 페이지 구분이다. PDF는 이 원본을 읽어 생성하므로 내용을 별도로 복제해서 편집하지 않는다. 목차 페이지는 구성이 달라지면 함께 갱신한다. 생성기는 표지의 대상 버전이 `CURRENT_RELEASE.display_version`과 다르면 실패하며, 출력 파일명·PDF 바닥글·메타데이터에 현재 앱 버전을 사용한다.

생성에는 Python의 `reportlab`, `pypdf`, 한글 TrueType 글꼴이 필요하다. 검증에는 `pymupdf`가 필요하다. 기본 글꼴은 Windows 맑은 고딕이다. 사용자 글꼴은 생성기의 `--font`와 `--bold-font`로 지정한다.

```powershell
python -m pip install reportlab pypdf pymupdf
python scripts/build_user_manual.py
```

화면은 앱 실행 의존성이 설치된 Windows Python 환경에서 다음 명령으로 다시 캡처한다. 사용자가 보는 창을 띄우거나 인증 키를 입력하지 않으며, 초기 설정 화면만 렌더링한다.

```powershell
python scripts/capture_user_manual.py
```

격리된 의존성 설치를 사용한 이번 작업의 재생성 명령:

```powershell
$env:PYTHONPATH = (Resolve-Path .tmp/manual-deps).Path
python scripts/build_user_manual.py
```

생성기는 의도한 페이지 수와 실제 PDF 페이지 수가 일치하는지 확인한다. 최종 배포 전에는 PDF 페이지를 이미지로 렌더링하여 한글·표·여백·화면 이미지 가독성을 확인한다. V26.0908은 전체 11쪽과 11개 책갈피, 목차 링크, 매 쪽의 버전·페이지 번호를 확인했고 11쪽 모두를 이미지로 렌더링해 검수했다.

2026-10-14에는 V26.1014 소스의 Windows 초기 화면을 다시 캡처하고 PDF를 새로 생성했다. 11쪽과 책갈피 11개, 목차 링크 20개, 표지 개정일 및 모든 쪽의 V26.1014·페이지 번호를 확인했다. PyMuPDF로 11쪽 전체를 렌더링해 한글·표·여백·화면 이미지와 바닥글을 검수했다. 이전 V26.0908 이미지와 PDF는 보관한다.

내용의 근거는 `mypackage/modern_gui_fixed.py`(버튼·옵션), `mypackage/start.py`(인증 흐름), `mypackage/gui.py`(입력·저장·결과·취소), `mypackage/result_view.py`(비교), `mypackage/gps2.py`(지도)다. 사용설명서에는 인증 키 값, 개발자용 설치·빌드 절차, 미공개 배포 링크를 넣지 않았다.

현재 소스와 새로 캡처한 GUI 화면을 대조해 작성했다. V26.0908부터 반영한 중복 버튼 제거와 실행별 저장 폴더, GPS 지도 저장 위치 안내를 유지했다. 실제 Windows 배포 EXE의 실행·탐지·저장 경로를 이번 문서 작업에서 검증한 것은 아니다. 저장 경로는 소스의 `__file__` 위치에 의존하므로 단일 EXE 패키징은 임시 위치를 사용할 수 있다. 실제 배포본으로 인증, 사진 한 장, 짧은 영상, 결과 보관을 확인한 뒤 해당 버전의 설명서를 함께 배포한다. 이전 버전 EXE가 들어 있는 폴더에는 새 버전 설명서를 덮어 넣지 않는다.


## V26.1018 갱신

사진 선택·프리셋·100% 비교·실행 기록과 현장 수색 1순위 기능을 본문에 통합했다. 후보 확인·보고서와 실시간 알림·장면·기록 절차를 12~13쪽에 추가해 전체 13쪽으로 구성한다. V26.1014·V26.0908 PDF와 화면은 이전 기록으로 보존한다.

이번 PDF는 번들 Python의 reportlab·pypdf와 Noto Sans KR 정적 TrueType 글꼴을 사용한다. macOS에서의 재생성 예시는 다음과 같다. 임시 글꼴은 배포 자산에 포함하지 않는다.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/capture_user_manual.py
/Users/tenmoo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/build_user_manual.py \
  --font tmp/pdfs/fonts/NotoSansKR-Regular.ttf \
  --bold-font tmp/pdfs/fonts/NotoSansKR-Bold.ttf
```

최종 PDF의 A4 13쪽·책갈피 13개·목차 링크 24개·모든 쪽의 V26.1018 바닥글과 전 페이지 렌더링을 확인했다. 한글·표·화면 이미지·페이지 나눔에 잘림이 없는 것을 확인했다. V26.1018 Windows EXE·캡처보드 검증과 ZIP 공개는 별도이며 피드의 다운로드 상태는 준비 중이다.

같은 버전의 실행 재현 4건 수정 후 PDF를 다시 생성했다. 12쪽에 원본 확인 불가 시 보류만 허용·잘못된 기록에서 기존 창 유지 안내를, 13쪽에 실제 미탐지 관측으로 구간 분리·종료 직전 저장과 미저장 입력 재시도 안내를 반영했다. 페이지·책갈피·링크 수와 전 쪽 버전 바닥글을 재확인하고 13쪽 전체 및 변경한 12~13쪽을 렌더링해 검수했다.
