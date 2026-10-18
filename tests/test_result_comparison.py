from unittest.mock import Mock

import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QImageReader, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from mypackage import result_view


@pytest.fixture
def photos(tmp_path):
    image = Image.new("RGB", (4000, 3000), "white")
    for x in range(1970, 2030):
        for y in range(1470, 1530):
            image.putpixel((x, y), (255, 0, 0) if (x + y) % 2 else (0, 0, 0))
    original = tmp_path / "original.png"
    detected = tmp_path / "detected.png"
    image.save(original)
    image.save(detected)
    return original, detected


@pytest.fixture
def comparison(qt_application, photos):
    dialog = result_view.ResultComparisonDialog(*photos)
    dialog.show()
    qt_application.processEvents()
    yield dialog
    dialog.close()
    dialog.deleteLater()
    qt_application.processEvents()


def load_current_regions(dialog):
    for preview in dialog.previews:
        preview._detail_timer.stop()
        preview._load_visible_region()


def test_actual_size_reads_original_pixels_instead_of_enlarging_preview(comparison):
    comparison.actual_size_button.click()
    load_current_regions(comparison)

    for preview in comparison.previews:
        assert preview.source_size == QSize(4000, 3000)
        assert preview._preview.width() == result_view.PREVIEW_EDGE
        assert preview.zoom == 1.0
        assert preview._detail.size() == preview._detail_rect.size()
        x = 2000 - preview._detail_rect.x()
        y = 1500 - preview._detail_rect.y()
        assert preview._detail.pixelColor(x, y).name() == "#000000"
        assert preview._detail.pixelColor(x + 1, y).name() == "#ff0000"
    assert comparison.zoom_label.text() == "100%"


def test_wheel_and_drag_synchronize_zoom_and_position(comparison, qt_application):
    comparison.actual_size_button.click()
    first, second = comparison.previews
    event = QWheelEvent(
        QPointF(first.width() / 2, first.height() / 2),
        QPointF(first.mapToGlobal(QPoint(first.width() // 2, first.height() // 2))),
        QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False,
    )
    QApplication.sendEvent(second, event)
    assert first.zoom == second.zoom == 1.25
    before = QPointF(first.center)
    QTest.mousePress(first, Qt.MouseButton.LeftButton, pos=QPoint(180, 180))
    QTest.mouseMove(first, QPoint(240, 210))
    QTest.mouseRelease(first, Qt.MouseButton.LeftButton, pos=QPoint(240, 210))
    qt_application.processEvents()

    assert first.center == second.center
    assert first.center.x() < before.x()
    assert first.center.y() < before.y()
    load_current_regions(comparison)
    assert first._detail_rect == second._detail_rect


def test_keyboard_pan_and_fit_restore_both_photos(comparison, qt_application):
    comparison.actual_size_button.click()
    first, second = comparison.previews
    QTest.keyClick(second, Qt.Key.Key_Right)
    assert first.center.x() > 0.5
    assert first.center == second.center

    comparison.fit_button.click()
    qt_application.processEvents()

    for preview in comparison.previews:
        assert preview.fit_mode is True
        assert preview.center == QPointF(0.5, 0.5)
        assert preview.visible_source_rect().size() == preview.source_size
        assert preview.zoom == preview.fit_zoom()
    assert comparison.zoom_label.text() == "화면 맞춤"


def test_keyboard_zoom_and_fit_actions_work_from_the_photo(comparison):
    preview = comparison.previews[0]
    preview.setFocus()
    QTest.keyClick(preview, Qt.Key.Key_1)
    assert preview.zoom == 1.0
    QTest.keyClick(preview, Qt.Key.Key_Plus)
    assert preview.zoom == 1.25
    QTest.keyClick(preview, Qt.Key.Key_Minus)
    assert preview.zoom == 1.0
    QTest.keyClick(preview, Qt.Key.Key_Home)
    assert all(view.fit_mode for view in comparison.previews)


def test_controls_fit_a_560_pixel_window_and_have_accessible_names(
    comparison, qt_application, tmp_path
):
    comparison.resize(560, 440)
    qt_application.processEvents()

    assert comparison.width() == 560
    for button in (
        comparison.zoom_out_button, comparison.zoom_in_button,
        comparison.actual_size_button, comparison.fit_button,
    ):
        assert button.isVisible()
        assert button.isEnabled()
        assert button.accessibleName()
        assert button.height() >= 36
        assert comparison.rect().contains(button.geometry())
    assert comparison.grab().save(str(tmp_path / "comparison-560.png"))


@pytest.mark.parametrize("orientation", range(1, 9))
def test_native_regions_follow_exif_rotation_and_mirroring(
    qt_application, tmp_path, orientation
):
    image = Image.new("RGB", (2200, 1600), "white")
    draw = ImageDraw.Draw(image)
    for box, color in (
        ((0, 0, 800, 500), "red"), ((900, 0, 2199, 799), "green"),
        ((0, 650, 999, 1599), "blue"), ((1050, 1000, 2199, 1599), "yellow"),
    ):
        draw.rectangle(box, fill=color)
    exif = Image.Exif()
    exif[274] = orientation
    photo = tmp_path / f"orientation-{orientation}.jpg"
    image.save(photo, quality=95, exif=exif)
    reader = QImageReader(str(photo))
    reader.setAutoTransform(True)
    reference = reader.read()
    dialog = result_view.ResultComparisonDialog(photo, photo)
    try:
        dialog.show()
        qt_application.processEvents()
        dialog._sync_view(1.0, QPointF(0.3, 0.4))
        load_current_regions(dialog)
        for preview in dialog.previews:
            assert preview.source_size == reference.size()
            rect = preview._detail_rect
            assert preview._detail.size() == rect.size()
            for x in range(10, rect.width(), 73):
                for y in range(10, rect.height(), 71):
                    assert preview._detail.pixelColor(x, y) == reference.pixelColor(
                        rect.x() + x, rect.y() + y
                    )
    finally:
        dialog.close()
        dialog.deleteLater()
        qt_application.processEvents()


def test_large_non_region_format_is_rejected_before_decode(qt_application, monkeypatch):
    reader = Mock()
    reader.size.return_value = QSize(12_000, 12_000)
    reader.supportsOption.return_value = False
    monkeypatch.setattr(result_view, "QImageReader", lambda path: reader)

    preview = result_view.PhotoPreview("large-image.png")

    assert preview._preview is None
    assert "메모리 보호" in preview._error
    reader.read.assert_not_called()
    preview.deleteLater()


def test_native_region_does_not_allocate_beyond_view_budget(
    comparison, monkeypatch
):
    preview = comparison.previews[0]
    comparison.actual_size_button.click()
    monkeypatch.setattr(result_view, "MAX_REGION_PIXELS", 100)
    preview._detail_timer.stop()
    preview._load_visible_region()

    assert preview._detail is None
    assert "표시 영역이 너무 큽니다" in preview._region_error


def test_replaced_file_dimensions_require_reopening_before_native_read(
    comparison, photos
):
    Image.new("RGB", (32, 32), "red").save(photos[0])
    comparison.actual_size_button.click()
    load_current_regions(comparison)

    assert comparison.previews[0]._detail is None
    assert "사진 파일이 변경되었습니다" in comparison.previews[0]._region_error
