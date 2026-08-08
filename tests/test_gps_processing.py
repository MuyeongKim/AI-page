import importlib
import sys
import types
from pathlib import Path


def test_list_original_images_in_folder_excludes_nested_original_copies(tmp_path):
    gps2 = load_gps2_with_test_stubs()

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
    gps2 = load_gps2_with_test_stubs()

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

    def fake_plot(locations, output_html="map.html", open_browser=True):
        plotted["locations"] = locations
        plotted["output_html"] = output_html
        plotted["open_browser"] = open_browser

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


def test_process_image_paths_skips_missing_unsupported_and_malformed_files(
    tmp_path, monkeypatch
):
    gps2 = load_gps2_with_test_stubs()

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
        lambda locations, output_html="map.html", open_browser=True: plotted.append(locations),
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
    gps2 = load_gps2_with_test_stubs()

    output_path = gps2._resolve_map_output_path("map.html")

    assert output_path == (gps2.DEFAULT_MAP_OUTPUT_DIR / "map.html").resolve()


def test_map_privacy_metadata_is_available_to_callers():
    gps2 = load_gps2_with_test_stubs()

    assert gps2.USES_EXTERNAL_TILES is True
    assert gps2.MAP_STORES_EXACT_COORDINATES is True
    assert "OpenStreetMap" in gps2.MAP_PRIVACY_NOTICE


def test_generated_map_files_are_ignored():
    project_root = Path(__file__).resolve().parents[1]
    ignore_rules = (project_root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/map*.html" in ignore_rules
    assert "/mypackage/map*.html" in ignore_rules


def load_gps2_with_test_stubs():
    sys.modules["exifread"] = types.ModuleType("exifread")
    sys.modules["folium"] = types.ModuleType("folium")
    sys.modules.pop("mypackage.gps2", None)
    return importlib.import_module("mypackage.gps2")
