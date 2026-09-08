# Detection output and bundled icons implementation plan

**Goal:** Fix the missing dropdown icon in packaged builds, remove the duplicate folder button from detection settings, and separate each detection run into its own folder.

**Architecture:** Compile the existing SVG into an imported Qt resource module so it travels with Python code. Allocate a timestamped directory atomically beneath the existing `DETECTED_OUTPUT_DIR` for each run. The worker returns that directory to the existing results tab and GPS workflow.

**Tech Stack:** Python, PySide6, Qt resources, pytest.

## Decisions

- Use `detected_files/YYYYMMDD_HHMMSS`, adding `_1`, `_2`, etc. when the name is already occupied. Keep existing files and per-run file collision protection.
- Use the detection start time, even if model loading takes time. Model-load failure or cancellation before analysis does not point to a previous result directory.
- Keep only `작업 결과 → 저장 폴더 열기`. Its existing last-result behavior also permits viewing files preserved from partial or cancelled work.
- Embed the SVG via `resources.qrc` and generated `resources_rc.py`; preserve direct execution of the layout module.

## Implementation and checks

1. Add a regression that renders the GUI with a simulated bundled module path containing no external SVG. Confirm the current implementation logs the missing-file error.
2. Add repeated-run tests for photos/videos, fixed-time directory collisions, concurrent allocation, and directory-creation/model failures. Confirm failures before implementation.
3. Add the Qt resource, generate its Python module with `pyside6-rcc`, and switch the stylesheet URL to the resource.
4. Remove the duplicate widget, connection, state, styles, and dead handlers in `modern_gui_fixed.py` and `gui.py`. Adapt folder-button checks to the results tab.
5. Implement `create_run_output_folder` in `output_storage.py` and use it in `DetectionWorker.run`. Emit the actual run path for results and GPS.
6. Update usage documentation to describe run directories and the retained folder button. Preserve existing user changes.
7. Run focused pytest checks, the desktop test suite, Ruff, and `git diff --check`. Inspect the rendered GUI and check resource loading in a minimal packaged executable.

The existing V26.0905 executable needs rebuilding to include Python changes. Its reported missing external SVG can also be restored locally without replacing the executable or release archive.

## Verification results

- Reproduced the missing SVG and shared run directory before implementation; seven new assertions failed as expected.
- All 184 desktop tests passed with `C:/Users/tenmo/anaconda3/envs/AI-making313/python.exe -m pytest -q -p no:cacheprovider --tb=short`.
- The three initial Windows test failures also occurred on unchanged HEAD: startup had already selected GPU, a Qt local URL used forward slashes, and the offscreen plugin lacked its font directory. Adjusted test setup/assertions without changing application behavior.
- Ruff's `E4,E7,E9,F` checks passed for `mypackage tests scripts AI-detection.py memory_monitor.py`. Installed Ruff 0.16.4's broader default rules report existing repository findings outside this change.
- Rendered the layout and loaded the icon from a minimal PyInstaller executable without external SVG data. The test bundle initially collected an incompatible Conda `icuuc.dll`; using the Windows ICU DLL loaded by the source application resolved the test-bundle startup error. This bundle is only a verification artifact in `.tmp`.
- A read-only code review found no blocking issues in output, cancellation, GPS, or resource handling.
- Restored the missing SVG in the local `output/AI객체탐지프로그램 V26.0905(디렉토리)/_internal/mypackage/icons` folder and verified its hash against the source. The existing EXE and release ZIP were not rebuilt.
