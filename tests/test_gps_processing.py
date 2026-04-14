import importlib
import sys
import types


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


def test_process_image_paths_uses_current_sources_only_and_deduplicates(monkeypatch):
    gps2 = load_gps2_with_test_stubs()

    calls = []

    def fake_extract(path):
        calls.append(path)
        mapping = {
            "a.jpg": (35.1, 127.1),
            "b.jpg": (35.2, 127.2),
            "c.jpg": None,
        }
        return mapping[path]

    plotted = {}

    def fake_plot(locations, output_html="map.html", open_browser=True):
        plotted["locations"] = locations
        plotted["output_html"] = output_html
        plotted["open_browser"] = open_browser

    monkeypatch.setattr(gps2, "extract_gps_data", fake_extract)
    monkeypatch.setattr(gps2, "plot_location_on_map", fake_plot)

    count = gps2.process_image_paths(["a.jpg", "a.jpg", "b.jpg", "c.jpg"], open_browser=False)

    assert count == 2
    assert calls == ["a.jpg", "b.jpg", "c.jpg"]
    assert plotted["locations"] == [(35.1, 127.1), (35.2, 127.2)]
    assert plotted["open_browser"] is False


def load_gps2_with_test_stubs():
    sys.modules["exifread"] = types.ModuleType("exifread")
    sys.modules["folium"] = types.ModuleType("folium")
    sys.modules.pop("mypackage.gps2", None)
    return importlib.import_module("mypackage.gps2")
