# Startup Device Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 인증 성공 시 앱 버전과 자동 감지된 추론 장치를 한 번에 안내하고, 메인 GUI의 장치 선택창을 실제 `GPU`, `MPS`, `CPU` 값으로 미리 설정한다.

**Architecture:** PyTorch가 실제 사용할 수 있는 가속 백엔드를 `CUDA → MPS → CPU` 순서로 판정한다. 인증 모듈은 성공 직후 같은 판정 결과와 `CURRENT_RELEASE` 버전을 기존 성공 알림에 표시하고, GUI는 시작 시 같은 판정 함수를 사용해 장치 상태와 콤보박스의 표시값을 일치시킨다. 단순 그래픽카드 존재 여부가 아니라 현재 PyTorch 빌드에서 사용 가능한지를 기준으로 안전하게 CPU로 대체한다.

**Tech Stack:** Python, PyTorch, PySide6, pytest.

---

### Task 1: 장치 판정과 사용자 안내 문구 명세

**Files:**
- Create: `tests/test_startup_device.py`
- Modify: `mypackage/gui.py:136-151`
- Modify: `mypackage/start.py:104-191`

**Step 1: Write the failing tests**

- CUDA 사용 가능 시 `cuda`, CUDA 없이 MPS 사용 가능 시 `mps`, 둘 다 없으면 `cpu`가 선택되는지 검증한다.
- 각 장치에 대해 사용자 안내 문구가 `GPU`, `MPS`, `CPU` 설정 결과와 이유를 포함하는지 검증한다.
- 인증 성공 알림 내용에 `CURRENT_RELEASE.display_version`과 장치 안내 문구가 함께 포함되는지 검증한다.

**Step 2: Run test to verify RED**

Run: `python -m pytest tests/test_startup_device.py -q -p no:cacheprovider`

Expected: FAIL because the startup-device message API does not exist yet.

### Task 2: 인증 성공 알림에 버전과 장치 결과 통합

**Files:**
- Modify: `mypackage/start.py:18-250`
- Test: `tests/test_startup_device.py`

**Step 1: Write minimal implementation**

- 인증키가 일치한 뒤 선호 장치를 판정한다.
- 기존 인증 성공 `QMessageBox` 하나에 버전과 장치 설정 결과를 함께 표시한다.
- 모던 스타일 적용 실패로 기본 인증을 사용할 때도 같은 정보를 표시한다.

**Step 2: Run focused tests to verify GREEN**

Run: `python -m pytest tests/test_startup_device.py tests/test_authentication.py -q -p no:cacheprovider`

Expected: PASS.

### Task 3: GUI 선택창을 실제 자동 감지 결과로 설정

**Files:**
- Modify: `mypackage/gui.py:960-1082`
- Test: `tests/test_startup_device.py`

**Step 1: Extend the failing test**

- 선호 장치 함수를 `cuda`, `mps`, `cpu`로 각각 대체해 `Ui_MainWindow`를 만들고 장치 콤보박스의 실제 표시값과 내부 `device`가 일치하는지 검증한다.

**Step 2: Run test to verify RED**

Run: `python -m pytest tests/test_startup_device.py -q -p no:cacheprovider`

Expected: FAIL because the combo box still selects `자동`.

**Step 3: Write minimal implementation**

- `sync_control_defaults()`가 감지된 장치를 `GPU`, `MPS`, `CPU` 라벨로 변환해 콤보박스에 선택한다.
- `자동` 항목은 사용자의 재감지 선택을 위해 유지한다.

**Step 4: Run focused tests to verify GREEN**

Run: `python -m pytest tests/test_startup_device.py tests/test_regressions.py -q -p no:cacheprovider`

Expected: PASS.

### Task 4: V26.08.25 릴리스 메타데이터와 문서 갱신

**Files:**
- Modify: `mypackage/version.py:37-76`
- Modify: `tests/test_version.py:20-36`
- Modify: `README.md:7-176`
- Generate: `latest_version.json`

**Step 1: Update version expectations first**

- 테스트의 현재 버전 기대값을 `26.08.25`로 바꾸고 새 변경 이력 핵심 문구를 검증한다.

**Step 2: Run test to verify RED**

Run: `python -m pytest tests/test_version.py -q -p no:cacheprovider`

Expected: FAIL because `CURRENT_RELEASE` is still `26.08.17`.

**Step 3: Update release sources and documentation**

- `CURRENT_RELEASE` 버전·날짜와 최상단 변경 이력을 갱신한다.
- README 현재 버전과 최근 변경 사항에 장치 자동 설정, 시작 알림, 탐지 폴더 열기, 인증 입력 안정화를 기록한다.
- `python scripts/export_release.py`로 `latest_version.json`을 재생성한다.

**Step 4: Run release consistency tests**

Run: `python -m pytest tests/test_version.py tests/test_export_release.py -q -p no:cacheprovider`

Run: `python scripts/export_release.py --check`

Expected: PASS and the feed matches `CURRENT_RELEASE`.

### Task 5: 전체 검증, 커밋, 푸시

**Files:**
- Verify: all changed files

**Step 1: Run project verification**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q -p no:cacheprovider`

Run: `ruff check .`

Run: `git diff --check`

Run: `Push-Location site; npm test; Pop-Location`

**Step 2: Review the exact commit scope**

Run: `git status --short`

Run: `git diff --stat`

Run: `git diff --cached --check`

**Step 3: Commit in Korean and push**

Run: `git commit -m "시작 장치 자동 설정과 V26.08.25 반영"`

Run: `git push origin main`

Expected: the commit is created on `main` and the remote accepts the push.
