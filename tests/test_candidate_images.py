from pathlib import Path

import cv2
import numpy as np
import pytest

from mypackage.candidate_images import candidate_thumbnail, save_candidate_thumbnail


def test_thumbnail_uses_candidate_pixels_and_clamps_edges():
    image = np.zeros((200, 300, 3), dtype=np.uint8)
    image[:100, :100] = [0, 0, 255]
    data = candidate_thumbnail(image, [0, 0, 10, 20])
    decoded = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    assert max(decoded.shape[:2]) == 480
    assert decoded[30, 30, 2] > 230
    assert decoded[30, 30, 0] < 20
    with pytest.raises(ValueError):
        candidate_thumbnail(image, [200, 10, 100, 20])
    with pytest.raises(ValueError):
        candidate_thumbnail(image, [0, 0, float('nan'), 20])


def test_thumbnail_atomic_failure_keeps_previous_file(tmp_path, monkeypatch):
    import mypackage.run_report as storage
    candidate = {'id': 'photo-000001-person-001', 'box': [10, 10, 20, 30]}
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    path = save_candidate_thumbnail(tmp_path, candidate, image)
    previous = (tmp_path / path).read_bytes()

    def fail(*args):
        raise OSError('disk full')

    monkeypatch.setattr(storage.os, 'replace', fail)
    with pytest.raises(OSError):
        save_candidate_thumbnail(tmp_path, candidate, image)
    assert (tmp_path / path).read_bytes() == previous
    assert not list((tmp_path / path).parent.glob('*.tmp'))
    assert not list((tmp_path / path).parent.glob('.*.tmp'))
    assert Path(path).parts[0] == 'candidates'
