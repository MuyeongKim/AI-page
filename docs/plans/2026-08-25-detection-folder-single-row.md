# Detection Folder Single-Row Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 탐지 대상의 `전체`, `사람만`, `차량만`과 `탐지 폴더 열기` 버튼을 같은 가로 한 줄에 순서대로 배치한다.

**Architecture:** `ModernUi_MainWindow._build_settings_card()`의 탐지 대상 영역을 하나의 `QHBoxLayout`으로 단순화한다. 최소 창 너비에서도 네 컨트롤이 보이도록 탐지 대상 제목은 위에 두고 컨트롤 행은 그리드 두 열 전체를 사용한다. 버튼의 활성화 조건과 폴더 열기 동작은 `Ui_MainWindow`에 그대로 둔다.

**Tech Stack:** Python, PySide6 Widgets, pytest.

---

### Task 1: 한 줄 배치 회귀 테스트

**Files:**
- Modify: `tests/test_result_folder_button.py:47-58`

**Step 1: Write the failing test**

- 최소 창 너비에서 네 컨트롤의 화면상 중심 Y 좌표가 같은지 확인한다.
- 화면상 X 좌표가 `전체 → 사람만 → 차량만 → 탐지 폴더 열기` 순서인지 확인한다.
- 마지막 버튼의 오른쪽 끝이 스크롤 영역 viewport를 벗어나지 않는지 유지한다.

**Step 2: Run test to verify RED**

Run: `$env:QT_QPA_PLATFORM='offscreen'; C:\Users\tenmo\anaconda3\envs\AI-making313\python.exe -m pytest tests/test_result_folder_button.py::test_detection_target_controls_share_one_row_at_minimum_width -q -p no:cacheprovider`

Expected: FAIL because the current layout places the first two controls and the last two controls on separate rows.

### Task 2: 탐지 대상 영역을 하나의 가로 레이아웃으로 변경

**Files:**
- Modify: `mypackage/modern_gui_fixed.py:287-306`
- Test: `tests/test_result_folder_button.py`

**Step 1: Write minimal implementation**

- 중첩된 `QVBoxLayout`, `detect_scope_row`, `detect_folder_row`를 제거한다.
- 하나의 `QHBoxLayout`에 `radioButton_all`, `radioButton_person`, `radioButton_car`, `pushButton_open_output_folder`, stretch를 순서대로 추가한다.
- 첫 번째 라디오 버튼 표시를 요청한 문구인 `전체`로 정리한다.
- 탐지 대상 제목은 컨트롤 위에 두고 컨트롤 행은 그리드의 두 열을 모두 사용한다.

**Step 2: Run focused tests to verify GREEN**

Run: `$env:QT_QPA_PLATFORM='offscreen'; C:\Users\tenmo\anaconda3\envs\AI-making313\python.exe -m pytest tests/test_result_folder_button.py -q -p no:cacheprovider`

Expected: PASS.

### Task 3: 전체 검증과 배포

**Files:**
- Verify: all changed files

**Step 1: Run project tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; C:\Users\tenmo\anaconda3\envs\AI-making313\python.exe -m pytest -q -p no:cacheprovider`

**Step 2: Run scoped lint and diff checks**

Run: `C:\Users\tenmo\anaconda3\envs\AI-making313\python.exe -m ruff check tests/test_result_folder_button.py`

Run: `git diff --check`

**Step 3: Commit and push**

Run: `git commit -m "탐지 대상과 결과 폴더 버튼을 한 줄로 정렬"`

Run: `git push origin main`
