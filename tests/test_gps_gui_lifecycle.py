import threading
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from mypackage import gui


@pytest.fixture(scope="module")
def gps_app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def gps_window(gps_app, monkeypatch):
    monkeypatch.setattr(gui.OnlineNoticeLoader, "refresh", lambda self: None)
    monkeypatch.setattr(QMessageBox, "information", Mock())
    monkeypatch.setattr(QMessageBox, "warning", Mock())
    window = gui.Ui_MainWindow()
    monkeypatch.setattr(window, "confirm_exit", lambda: True)
    yield window
    if window._gps_worker is not None:
        window._gps_worker.requestInterruption()
        assert window._gps_worker.wait(3_000)
        gps_app.processEvents()
    window._closing_without_confirmation = True
    window.close()
    window.deleteLater()
    gps_app.processEvents()


def test_late_cancel_preserves_completed_map_without_opening_browser(
    gps_window, monkeypatch, tmp_path
):
    map_path = tmp_path / "map.html"
    map_path.write_text("<html>completed map</html>", encoding="utf-8")
    browser = Mock(return_value=True)
    monkeypatch.setattr(gui.gps2, "open_map_in_browser", browser)
    gps_window._cancel_requested = True
    gps_window._pending_gps_outcome = (
        gui.gps2.GPSProcessingResult(1, 1, 0, (), map_path), ""
    )

    gps_window._finish_gps_mapping()

    browser.assert_not_called()
    assert map_path.read_text(encoding="utf-8") == "<html>completed map</html>"
    summary = gps_window.result_summary.toPlainText()
    assert "취소" in summary
    assert str(map_path) in summary
    assert gps_window._processing is False


def test_close_waits_for_queued_finished_even_after_native_thread_exits(
    gps_window, gps_app, monkeypatch, tmp_path
):
    map_path = tmp_path / "map.html"
    map_path.write_text("<html>completed map</html>", encoding="utf-8")
    browser = Mock(return_value=True)
    monkeypatch.setattr(gui.gps2, "open_map_in_browser", browser)
    monkeypatch.setattr(
        gui.gps2,
        "process_image_paths_detailed",
        lambda *args, **kwargs: gui.gps2.GPSProcessingResult(1, 1, 0, (), map_path),
    )
    gps_window.show()
    gps_window.start_gps_mapping([], tmp_path)
    native_worker = gps_window._gps_worker
    assert native_worker.wait(3_000)
    assert not native_worker.isRunning()
    assert gps_window._gps_worker is native_worker

    # The native thread is done, but its queued outcome/finished slots have not run.
    gps_window.close()

    assert gps_window._close_after_gps is True
    assert gps_window.isVisible()
    assert gps_window._cleanup_done is False
    gps_app.processEvents()

    assert gps_window._gps_worker is None
    assert not gps_window.isVisible()
    assert gps_window._cleanup_done is True
    browser.assert_not_called()
    QMessageBox.information.assert_not_called()
    QMessageBox.warning.assert_not_called()


def test_cancel_during_map_save_keeps_file_and_suppresses_automatic_open(
    gps_window, gps_app, monkeypatch, tmp_path
):
    image_path = tmp_path / "original_photo.jpg"
    image_path.write_bytes(b"test EXIF source")
    entered_save = threading.Event()
    release_save = threading.Event()
    original_save = gui.gps2.folium.Map.save

    def blocking_save(map_object, *args, **kwargs):
        entered_save.set()
        assert release_save.wait(3)
        return original_save(map_object, *args, **kwargs)

    browser = Mock(return_value=True)
    monkeypatch.setattr(gui.gps2, "extract_gps_data", lambda path: (37.5, 127.0))
    monkeypatch.setattr(gui.gps2.folium.Map, "save", blocking_save)
    monkeypatch.setattr(gui.gps2, "open_map_in_browser", browser)
    gps_window.start_gps_mapping([image_path], tmp_path)
    native_worker = gps_window._gps_worker
    try:
        assert entered_save.wait(3)
        gps_window.cancel_detection()
        assert gps_window._cancel_requested is True
    finally:
        release_save.set()
    assert native_worker.wait(3_000)
    gps_app.processEvents()

    assert (tmp_path / "map.html").is_file()
    browser.assert_not_called()
    assert gps_window._gps_worker is None
    assert "취소" in gps_window.result_summary.toPlainText()
    assert str(tmp_path / "map.html") in gps_window.result_summary.toPlainText()
