# 사용설명서 관리

- 편집 원본: `docs/사용설명서.md`
- PDF: `output/pdf/Stay-Up-AI-사용설명서-V26.0908.pdf`
- 생성기: `scripts/build_user_manual.py`
- 기준: `mypackage/version.py`의 V26.0908, 2026-09-08 개정
- 화면: `docs/images/manual-main-V26.0908.png`. 현재 소스의 실제 Windows GUI를 `scripts/capture_user_manual.py`로 캡처한다. 기존 웹사이트 화면과 별도로 설명서 버전에 맞춰 관리한다.

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

내용의 근거는 `mypackage/modern_gui_fixed.py`(버튼·옵션), `mypackage/start.py`(인증 흐름), `mypackage/gui.py`(입력·저장·결과·취소), `mypackage/result_view.py`(비교), `mypackage/gps2.py`(지도)다. 사용설명서에는 인증 키 값, 개발자용 설치·빌드 절차, 미공개 배포 링크를 넣지 않았다.

현재 소스와 새로 캡처한 Windows 화면을 대조해 작성했다. V26.0908의 중복 버튼 제거와 실행별 저장 폴더, GPS 지도 저장 위치를 반영했다. 실제 Windows 배포 EXE의 실행·탐지·저장 경로를 이번 문서 작업에서 검증한 것은 아니다. 저장 경로는 소스의 `__file__` 위치에 의존하므로 단일 EXE 패키징은 임시 위치를 사용할 수 있다. 실제 배포본으로 인증, 사진 한 장, 짧은 영상, 결과 보관을 확인한 뒤 해당 버전의 설명서를 함께 배포한다. 이전 버전 EXE가 들어 있는 폴더에는 새 버전 설명서를 덮어 넣지 않는다.
