from pathlib import Path
from unittest.mock import Mock

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from mypackage import gui
from mypackage.result_view import PhotoPreview, ResultComparisonDialog


def test_progress_keeps_last_photo_counts_across_stage_and_cancel(qt_application):
    dialog = gui.DetectionProgressDialog("준비", 3)
    dialog.set_photo_result({"status": "completed", "filename": "<사진>.jpg", "people": 2,
                            "vehicles": 1, "total_people": 4, "total_vehicles": 1,
                            "processed": 2, "total": 3, "succeeded": 2, "failed": 0,
                            "detected_photos": 2})
    dialog.set_stage_progress("다음 사진 분석 중", 2, 3)
    assert "사람 후보 2건" in dialog.photo_summary.text()
    assert "누적 사람 후보 4건" in dialog.photo_summary.text()
    assert dialog.photo_summary.textFormat() == Qt.TextFormat.PlainText
    before = dialog.photo_summary.text()
    dialog.request_cancel()
    dialog.set_stage_progress("끝", 3, 3)
    assert "취소 요청됨" in dialog.label.text()
    assert dialog.photo_summary.text() == before
    dialog.finish()


def test_worker_emits_success_empty_and_failure_counts(qt_application, tmp_path):
    worker = gui.DetectionWorker({"source": "사진", "file_count": 3})
    summaries = []
    worker.photo_result_signal.connect(summaries.append)

    def process(source, *_args):
        success = source != "failed.jpg"
        worker.photo_records.append({"source": source, "status": "completed" if success else "failed",
                                     "people": [1, 2] if source == "people.jpg" else [],
                                     "vehicles": 1 if source == "people.jpg" else 0})
        return success

    worker.process_single_file = process
    for name in ("people.jpg", "empty.jpg", "failed.jpg"):
        worker.process_image_attempt(name, [], tmp_path)
    assert [s["people"] for s in summaries] == [2, 0, 0]
    assert summaries[-1]["status"] == "failed"
    assert summaries[-1]["total_people"] == 2
    assert summaries[-1]["total_vehicles"] == 1
    assert summaries[-1]["detected_photos"] == 1
    assert summaries[-1]["succeeded"] == 2 and summaries[-1]["failed"] == 1


def test_gallery_navigates_pairs_in_one_window_and_resets_fit(qt_application, tmp_path):
    items = []
    for i in range(3):
        original = tmp_path / f"original-{i}.png"
        output = tmp_path / f"detected-{i}.png"
        Image.new("RGB", (400 + i * 100, 300), "green").save(original)
        Image.new("RGB", (400 + i * 100, 300), "blue").save(output)
        items.append({"original": str(original), "output": str(output)})
    dialog = ResultComparisonDialog(None, None, items=items)
    dialog.show()
    qt_application.processEvents()
    changed = []
    dialog.current_changed.connect(changed.append)
    assert "사진 1 / 3" in dialog.item_label.text()
    dialog.actual_size_button.click()
    previous_previews = list(dialog.previews)
    dialog.next_button.click()
    assert all(not preview.isVisible() for preview in previous_previews)
    qt_application.processEvents()
    assert len([p for p in dialog.findChildren(PhotoPreview) if p.isVisible()]) == 2
    assert changed == [1] and dialog.previews[0].path == items[1]["original"]
    assert dialog.previews[1].path == items[1]["output"]
    assert dialog.previews[0].fit_mode
    QTest.keyClick(dialog.previews[1], Qt.Key.Key_PageDown)
    assert dialog.current_index == 2 and not dialog.next_button.isEnabled()
    dialog.previous_button.click()
    dialog.mode_button.click()
    qt_application.processEvents()
    assert not dialog.photo_columns[0].isVisible()
    assert dialog.photo_columns[1].isVisible()
    Path(items[2]["output"]).unlink()
    dialog.next_button.click()
    qt_application.processEvents()
    assert dialog.previews[1]._error
    dialog.previous_button.click()
    qt_application.processEvents()
    assert dialog.previews[1]._preview is not None
    dialog.close()
    dialog.deleteLater()
    qt_application.processEvents()


def test_main_result_open_uses_gallery_and_updates_selection(qt_application, tmp_path, monkeypatch):
    originals, outputs = [], []
    for i in range(2):
        original, output = tmp_path / f"o{i}.png", tmp_path / f"d{i}.png"
        for p in (original, output):
            Image.new("RGB", (120, 100), "white").save(p)
        originals.append(str(original))
        outputs.append(str(output))
    external = Mock(return_value=True)
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", external)
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    window.remember_detection_result({"original_files": originals, "output_files": outputs}, "검증")
    window.open_selected_result()
    qt_application.processEvents()
    dialog = window._comparison_dialog
    assert dialog.isVisible() and dialog.comparison_mode
    dialog.next_button.click()
    assert window.result_files_combo.currentIndex() == 1
    assert not external.called
    dialog.close()
    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    QApplication.processEvents()
