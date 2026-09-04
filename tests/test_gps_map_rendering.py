import pytest

from mypackage import gps2


def test_map_fits_all_locations_and_keeps_filenames_as_safe_text(tmp_path):
    filename = "original_<img onerror=alert(1)>`${alert(2)}.jpg"
    output = gps2.plot_location_on_map(
        [(37.5665, 126.978), (35.1796, 129.0756)],
        output_html=tmp_path / "map.html",
        open_browser=False,
        photo_names=[tmp_path / "private-source" / filename, "second.jpg"],
    )

    document = output.read_text(encoding="utf-8")
    assert ".fitBounds(" in document
    assert "[[37.5665, 126.978], [35.1796, 129.0756]]" in document
    assert "private-source" not in document
    assert "&lt;img onerror=alert(1)&gt;" in document
    assert "&#96;&#36;{alert(2)}" in document
    assert "${alert(2)}" not in document
    assert "<img onerror" not in document
    assert "second.jpg" in document


def test_coincident_markers_keep_the_useful_default_zoom(tmp_path):
    output = gps2.plot_location_on_map(
        [[37.5, 127.0], [37.5, 127.0]],
        output_html=tmp_path / "map.html",
        open_browser=False,
    )

    document = output.read_text(encoding="utf-8")
    assert ".fitBounds(" not in document
    assert '"zoom": 15' in document


def test_cancel_before_map_save_does_not_publish_a_file(tmp_path):
    output = tmp_path / "map.html"

    with pytest.raises(InterruptedError, match="GPS 분석이 취소되었습니다"):
        gps2.plot_location_on_map(
            [(37.5, 127.0)],
            output_html=output,
            open_browser=False,
            should_cancel=lambda: True,
        )

    assert not output.exists()
