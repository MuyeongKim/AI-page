import pytest

from mypackage.video_source import normalize_source_name, resolve_video_source_path


def test_normalize_source_name_accepts_both_capture_board_spellings():
    assert normalize_source_name("외부영상(캡처보드)") == "외부영상(캡처보드)"
    assert normalize_source_name("외부영상(캡쳐보드)") == "외부영상(캡처보드)"


def test_resolve_video_source_path_uses_file_path_for_recorded_video():
    assert resolve_video_source_path("영상", ["sample.mp4"]) == "sample.mp4"


def test_resolve_video_source_path_defaults_to_device_zero_for_capture_board():
    assert resolve_video_source_path("외부영상(캡처보드)", None) == 0
    assert resolve_video_source_path("외부영상(캡처보드)", "") == 0


def test_resolve_video_source_path_parses_capture_device_index():
    assert resolve_video_source_path("외부영상(캡처보드)", "2") == 2


def test_resolve_video_source_path_rejects_invalid_capture_device_text():
    with pytest.raises(ValueError):
        resolve_video_source_path("외부영상(캡처보드)", "usb-capture")
