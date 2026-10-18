from pathlib import Path

import numpy as np
import pytest

from mypackage import gui
from mypackage.photo_input import collect_photo_inputs


def test_nested_dcim_count_matches_processed_files_and_preserves_same_names(tmp_path, monkeypatch):
    root = tmp_path / 'SD'
    sources = []
    for folder in ('DCIM/100MEDIA', 'DCIM/101MEDIA'):
        photo = root / folder / 'DJI_0001.JPG'
        photo.parent.mkdir(parents=True)
        photo.write_bytes(folder.encode())
        sources.append(photo)
    excluded = root / 'detected_files'
    excluded.mkdir()
    (excluded / 'old.jpg').touch()
    monkeypatch.setattr(gui, 'DETECTED_OUTPUT_DIR', excluded)
    window = gui.Ui_MainWindow()
    assert window.count_image_files(root) == 2
    window._closing_without_confirmation = True
    window.close()
    worker = gui.DetectionWorker({'source': '사진', 'juso': [root, sources[0]],
                                  'classes_to_detect': [0], 'file_count': 2})

    class Result:
        names = {0: 'person'}
        boxes = type('Boxes', (), {'cls': np.array([0])})()

        def save(self, filename):
            Path(filename).write_bytes(b'ANNOTATED')

    worker.model = lambda *args, **kwargs: [Result()]
    detected = []
    worker.process_images(excluded / 'new', detected)
    assert detected == [str(path) for path in sources]
    assert worker.attempted_count == 2
    assert len(set(worker.output_files)) == 2
    assert [Path(path).read_bytes() for path in worker.original_files] == [
        path.read_bytes() for path in sources
    ]


def test_scan_skips_symlink_cycles_and_duplicate_paths(tmp_path):
    photo = tmp_path / 'a.jpg'
    photo.touch()
    try:
        (tmp_path / 'cycle').symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks not available')
    paths, errors = collect_photo_inputs([tmp_path, photo, photo])
    assert paths == [str(photo)]
    assert errors == []


def test_scan_reports_read_failure_and_honors_cancel(tmp_path, monkeypatch):
    import mypackage.photo_input as photo_input

    def failed_walk(root, *, onerror, **kwargs):
        onerror(PermissionError(13, 'denied', str(root)))
        return iter(())

    monkeypatch.setattr(photo_input.os, 'walk', failed_walk)
    paths, errors = collect_photo_inputs([tmp_path])
    assert not paths
    assert any('denied' in error for error in errors)
    assert collect_photo_inputs([tmp_path], should_cancel=lambda: True) == ([], [])
