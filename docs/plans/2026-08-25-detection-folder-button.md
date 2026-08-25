# Detection Folder Button Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a disabled-by-default `탐지 폴더 열기` button beside the vehicle-only target control, then enable it after a completed or partially completed detection run produces an existing output folder.

**Architecture:** The generated UI owns the button and its layout/accessibility styling. `Ui_MainWindow` owns the last completed result-folder path, derives the enabled state from that path plus the processing state, and delegates opening to Qt's cross-platform desktop service. The worker result's `output_folder` field remains the single source of truth.

**Tech Stack:** Python, PySide6 Widgets, `pathlib.Path`, pytest.

---

### Task 1: Specify the button state and folder-opening behavior

**Files:**
- Create: `tests/test_result_folder_button.py`
- Reference: `mypackage/gui.py`
- Reference: `mypackage/modern_gui_fixed.py`

**Step 1: Write failing tests**

- Assert the generated main window exposes `pushButton_open_output_folder` and starts disabled.
- Feed a terminal result whose `output_folder` is an existing temporary directory and assert the button becomes enabled only after processing ends.
- Patch `QDesktopServices.openUrl`, click the button, and assert it receives a local-file URL for the exact result directory.
- Remove the directory and assert the action disables itself and shows a warning instead of opening a stale path.

**Step 2: Run tests to verify RED**

Run: `pytest tests/test_result_folder_button.py -q`

Expected: FAIL because the button and result-folder state do not exist yet.

### Task 2: Add the button to the detection-target row

**Files:**
- Modify: `mypackage/modern_gui_fixed.py:162-181`
- Modify: `mypackage/modern_gui_fixed.py:283-290`
- Modify: `mypackage/modern_gui_fixed.py:364-460`
- Modify: `mypackage/modern_gui_fixed.py:567-624`

**Step 1: Implement the widget**

- Create `pushButton_open_output_folder` with label `탐지 폴더 열기` and disable it initially.
- Keep it immediately to the right of `radioButton_car`, using a two-line target layout so the controls remain visible at the existing 560 px minimum width.
- Add accessible name, description, tooltip, focus, hover, and disabled styles consistent with the existing secondary buttons.

### Task 3: Connect result state to the operating-system folder action

**Files:**
- Modify: `mypackage/gui.py:41-57`
- Modify: `mypackage/gui.py:958-1030`
- Modify: `mypackage/gui.py:1206-1244`
- Modify: `mypackage/gui.py:1640-1785`
- Modify: `mypackage/gui.py:1811-1845`

**Step 1: Implement minimal behavior**

- Store the last completed output folder as a `Path` or `None`.
- Connect the button to `open_detection_folder()`.
- Disable and clear the action when a new run starts.
- Record the result folder only for completed or partially completed structured results; failed, cancelled, and disconnected results must not reactivate an older folder.
- Enable the action only while idle and while the stored path is an existing directory.
- Open the folder with `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`; warn and disable for a stale path, and warn without disabling if the OS rejects an existing path.

**Step 2: Run tests to verify GREEN**

Run: `pytest tests/test_result_folder_button.py -q`

Expected: PASS.

### Task 4: Verify regressions and layout

**Files:**
- Verify: `mypackage/gui.py`
- Verify: `mypackage/modern_gui_fixed.py`
- Verify: `tests/test_result_folder_button.py`

**Step 1: Run focused and adjacent tests**

Run: `pytest tests/test_result_folder_button.py tests/test_result_status_ui.py tests/test_regressions.py -q`

**Step 2: Run static checks**

Run: `python -m compileall -q mypackage/gui.py mypackage/modern_gui_fixed.py tests/test_result_folder_button.py`

Run: `git diff --check`

**Step 3: Perform an offscreen UI smoke check**

- Confirm the button exists directly after `차량만`, starts disabled, enables for an existing completed-result folder, and remains fully visible without overlap at the existing 560 px minimum window width.

Do not commit unless the user explicitly requests a commit.
