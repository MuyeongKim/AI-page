import importlib
from pathlib import Path

import pytest


def test_list_original_images_in_folder_excludes_nested_original_copies(tmp_path):
    gps2 = load_gps2()

    (tmp_path / "original_a.jpg").write_bytes(b"a")
    (tmp_path / "original_b.png").write_bytes(b"b")
    (tmp_path / "original_original_c.jpg").write_bytes(b"c")
    (tmp_path / "detected_a.jpg").write_bytes(b"d")
    (tmp_path / "note.txt").write_text("x", encoding="utf-8")

    result = gps2.list_original_images_in_folder(tmp_path)

    assert result == [
        str(tmp_path / "original_a.jpg"),
        str(tmp_path / "original_b.png"),
    ]


def test_process_image_paths_uses_current_sources_only_and_deduplicates(tmp_path, monkeypatch):
    gps2 = load_gps2()

    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    without_gps = tmp_path / "without_gps.jpg"
    for path in (first, second, without_gps):
        path.write_bytes(b"image")

    calls = []

    def fake_extract(path):
        calls.append(path.name)
        mapping = {
            first.name: (1.0, 2.0),
            second.name: (3.0, 4.0),
            without_gps.name: None,
        }
        return mapping[path.name]

    plotted = {}

    def fake_plot(locations, output_html="map.html", open_browser=True, **kwargs):
        plotted["locations"] = locations
        plotted["output_html"] = output_html
        plotted["open_browser"] = open_browser
        plotted["photo_names"] = kwargs["photo_names"]
        return output_html

    monkeypatch.setattr(gps2, "extract_gps_data", fake_extract)
    monkeypatch.setattr(gps2, "plot_location_on_map", fake_plot)

    output_directory = tmp_path / "maps"
    count = gps2.process_image_paths(
        [first, first, second, without_gps],
        open_browser=False,
        output_directory=output_directory,
    )

    assert count == 2
    assert calls == [first.name, second.name, without_gps.name]
    assert plotted["locations"] == [(1.0, 2.0), (3.0, 4.0)]
    assert plotted["output_html"] == output_directory / "map.html"
    assert plotted["open_browser"] is False
    assert plotted["photo_names"] == [first.name, second.name]


def test_process_image_paths_skips_missing_unsupported_and_malformed_files(
    tmp_path, monkeypatch
):
    gps2 = load_gps2()

    malformed = tmp_path / "malformed.jpg"
    valid = tmp_path / "valid.jpg"
    unsupported = tmp_path / "notes.txt"
    missing = tmp_path / "missing.jpg"
    malformed.write_bytes(b"malformed")
    valid.write_bytes(b"valid")
    unsupported.write_text("not an image", encoding="utf-8")

    inspected = []

    def fake_extract(path):
        inspected.append(path.name)
        if path == malformed:
            raise TypeError("invalid EXIF structure")
        return (1.0, 2.0)

    plotted = []
    monkeypatch.setattr(gps2, "extract_gps_data", fake_extract)
    monkeypatch.setattr(
        gps2,
        "plot_location_on_map",
        lambda locations, **kwargs: plotted.append(locations),
    )

    count = gps2.process_image_paths(
        [missing, unsupported, malformed, valid],
        output_directory=tmp_path / "maps",
        open_browser=False,
    )

    assert count == 1
    assert inspected == [malformed.name, valid.name]
    assert plotted == [[(1.0, 2.0)]]


def test_relative_map_output_defaults_to_ignored_detection_directory():
    gps2 = load_gps2()

    output_path = gps2._resolve_map_output_path("map.html")

    assert output_path == (gps2.DEFAULT_MAP_OUTPUT_DIR / "map.html").resolve()


def test_map_privacy_metadata_is_available_to_callers():
    gps2 = load_gps2()

    assert gps2.USES_EXTERNAL_TILES is True
    assert gps2.MAP_STORES_EXACT_COORDINATES is True
    assert "OpenStreetMap" in gps2.MAP_PRIVACY_NOTICE


def test_generated_map_files_are_ignored():
    project_root = Path(__file__).resolve().parents[1]
    ignore_rules = (project_root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/map*.html" in ignore_rules
    assert "/mypackage/map*.html" in ignore_rules


def test_detailed_result_distinguishes_missing_gps_from_unreadable_images(
    tmp_path, monkeypatch
):
    gps2 = load_gps2()
    images = [tmp_path / name for name in ("gps.jpg", "no_gps.jpg", "broken.jpg")]
    for path in images:
        path.write_bytes(b"image")
    missing = tmp_path / "missing.jpg"

    def extract(path):
        if path.name == "broken.jpg":
            raise ValueError("invalid EXIF")
        return (37.5, 127.0) if path.name == "gps.jpg" else None

    monkeypatch.setattr(gps2, "extract_gps_data", extract)
    monkeypatch.setattr(
        gps2, "plot_location_on_map", lambda locations, **kwargs: kwargs["output_html"]
    )

    result = gps2.process_image_paths_detailed(
        [images[0], images[0], *images[1:], missing],
        output_directory=tmp_path,
        open_browser=False,
    )

    assert result.location_count == 1
    assert result.checked_count == 4
    assert result.no_gps_count == 1
    assert len(result.errors) == 2
    assert "broken.jpg" in result.errors[0]
    assert "missing.jpg" in result.errors[1]
    assert result.map_path == tmp_path / "map.html"


def test_cancel_between_images_stops_before_reading_next_image(tmp_path, monkeypatch):
    gps2 = load_gps2()
    images = [tmp_path / name for name in ("first.jpg", "second.jpg")]
    for path in images:
        path.write_bytes(b"image")
    inspected = []
    plotted = []
    monkeypatch.setattr(
        gps2, "extract_gps_data", lambda path: inspected.append(path) or (37.5, 127.0)
    )
    monkeypatch.setattr(gps2, "plot_location_on_map", lambda *args, **kwargs: plotted.append(1))

    with pytest.raises(InterruptedError, match="GPS 분석이 취소되었습니다"):
        gps2.process_image_paths_detailed(
            images, open_browser=False, should_cancel=lambda: bool(inspected)
        )

    assert inspected == images[:1]
    assert plotted == []


def test_no_gps_result_has_no_map_and_no_error(tmp_path, monkeypatch):
    gps2 = load_gps2()
    image = tmp_path / "no_gps.jpg"
    image.write_bytes(b"image")
    monkeypatch.setattr(gps2, "extract_gps_data", lambda path: None)

    result = gps2.process_image_paths_detailed([image], open_browser=False)

    assert result.location_count == 0
    assert result.checked_count == result.no_gps_count == 1
    assert result.errors == ()
    assert result.map_path is None


def load_gps2():
    return importlib.import_module("mypackage.gps2")
