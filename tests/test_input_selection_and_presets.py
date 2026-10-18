import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from mypackage import gui
from mypackage.selected_files import SelectedFilesDialog


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp):
    window = gui.Ui_MainWindow()
    window._online_notice_fetch_started = True
    yield window
    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_multi_photo_selection_survives_typing_and_applies_list_removal(
    window, tmp_path, monkeypatch, qapp
):
    paths = [str(tmp_path / name) for name in ("사진, 1.jpg", "사진 2.jpg", "사진 3.jpg")]
    for path in paths:
        with open(path, "wb") as stream:
            stream.write(b"source")
    monkeypatch.setattr(gui.QFileDialog, "getOpenFileNames", lambda *_args: (paths, ""))
    window.comboBox_source.setCurrentText("사진")
    window.comboBox_data.setCurrentText("YoloV26_최소")
    window.browse_files()
    window.show()
    qapp.processEvents()
    assert window.lineEdit_juso.text() == "사진 3장 선택됨"
    assert window.selected_files_button.text() == "선택 목록 · 3장"
    assert window.lineEdit_juso.isReadOnly()
    window.lineEdit_juso.setFocus()
    QTest.keyClicks(window.lineEdit_juso, " ")
    assert window.juso == paths
    assert window.pushButton_enter.isEnabled()

    def remove_second(dialog):
        dialog.files_list.item(1).setSelected(True)
        dialog.remove_button.click()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SelectedFilesDialog, "exec", remove_second)
    window.selected_files_button.click()
    assert window.juso == [paths[0], paths[2]]
    assert window.file_count == 2
    assert all(os.path.isfile(path) for path in paths)


def test_selection_dialog_can_cancel_or_exclude_all_without_deleting_files(window, tmp_path):
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"source")
    paths = [str(photo)]
    window.comboBox_source.setCurrentText("사진")
    window.set_selected_files(paths)
    dialog = SelectedFilesDialog(paths)
    dialog.files_list.selectAll()
    dialog.remove_button.click()
    assert dialog.selected_paths() == []
    dialog.reject()
    assert window.juso == paths
    assert photo.exists()
    window.set_selected_files([])
    assert window.file_count == 0
    assert window.juso is None
    assert not window.lineEdit_juso.isReadOnly()
    assert not window.selected_files_button.isEnabled()
    assert not window.pushButton_enter.isEnabled()


def test_switching_from_multi_photo_to_capture_restores_editable_input(window, tmp_path):
    window.comboBox_source.setCurrentText("사진")
    window.set_selected_files([str(tmp_path / "a.jpg"), str(tmp_path / "b.jpg")])
    window.comboBox_source.setCurrentText("외부영상(캡처보드)")
    assert not window.lineEdit_juso.isReadOnly()
    window.lineEdit_juso.setText("2")
    assert window.juso == "2"
    assert window.input_is_ready()
    assert not window.selected_files_button.isVisible()


@pytest.mark.parametrize(
    ("preset", "model", "size"),
    [("빠른 분석", "yolo26n.pt", 640), ("균형 분석", "yolo26s.pt", 1280),
     ("정밀 분석", "yolo26x.pt", 1920)],
)
def test_presets_apply_model_and_size_without_changing_target_or_confidence(
    window, preset, model, size
):
    window.comboBox_percentage.setCurrentText("30%")
    window.radioButton_person.setChecked(True)
    window.comboBox_preset.setCurrentText(preset)
    assert window.datasize == model
    assert window.imgsz == size
    assert window.percentage == pytest.approx(0.3)
    assert window.classes_to_detect == [0]
    assert window.comboBox_preset.currentText() == preset
    window.comboBox_imgsz.setCurrentText("1080")
    assert window.comboBox_preset.currentText() == "직접 설정"
    assert window.imgsz == 1080


@pytest.mark.parametrize(("device", "preset"), [("cpu", "빠른 분석"), ("cuda", "균형 분석"),
                                                  ("mps", "균형 분석")])
def test_device_recommendation_requires_explicit_apply(window, device, preset):
    assert window.datasize is None
    assert window.imgsz == 1920
    window.device = device
    window.update_preset_hint()
    assert preset in window.preset_hint.text()
    assert window.datasize is None
    window.recommend_preset_button.click()
    assert window.comboBox_preset.currentText() == preset


def test_active_work_disables_new_settings_and_selection_controls(window):
    window.set_processing_state(True)
    for control in (window.comboBox_preset, window.recommend_preset_button,
                    window.selected_files_button):
        assert not control.isEnabled()
    window.set_processing_state(False)
