import json

import cv2
import numpy as np
import pytest

from mypackage.search_report import create_search_report


def photo_record(tmp_path, count=8):
    cv2.imwrite(str(tmp_path / 'thumb.jpg'), np.zeros((20, 20, 3), dtype=np.uint8))
    path = tmp_path / 'detections.json'
    path.write_text(json.dumps({'schema_version': 1, 'status': 'partial', 'app_version': '26.1014',
        'photos': [{'id': 'p1', 'status': 'completed', 'source': '<script>alert(1).jpg',
                    'image_size': [100, 100], 'original_file': None, 'detected_file': None,
                    'gps': {'lat': 35, 'lon': 127}, 'warnings': ['metadata <bad>'],
                    'people': [{'id': f'c{i}', 'box': [10, 10, 20, 40],
                                'confidence': .5 + i / 100, 'review': 'person' if i == 0 else 'hold',
                                'thumbnail_file': 'thumb.jpg'} for i in range(count)]}]}))
    return path


def test_report_embeds_images_escapes_text_and_keeps_all_candidates(tmp_path):
    path = photo_record(tmp_path)
    output = create_search_report(path, {'status': 'partial', 'errors': ['read <failed>'],
                                         'model': 'yolo26x.pt', 'image_size': 1920})
    html = output.read_text()
    assert '<script>' not in html
    assert '&lt;script&gt;' in html and 'read &lt;failed&gt;' in html
    assert html.count('data:image/jpeg;base64,') == 6
    assert '촬영 위치' in html and '고유 인원' in html and '부분 완료' in html
    assert '사람 맞음 1' in html and '보류 7' in html
    assert all(f'c{i}' in html for i in range(8))
    assert 'https://' not in html and 'http://' not in html
    assert '1920' in html


def test_report_failure_preserves_previous_html(tmp_path, monkeypatch):
    import mypackage.run_report as storage
    path = photo_record(tmp_path, 0)
    output = tmp_path / 'search_report.html'
    output.write_text('OLD')

    def fail(*args):
        raise OSError('disk full')

    monkeypatch.setattr(storage.os, 'replace', fail)
    with pytest.raises(OSError):
        create_search_report(path)
    assert output.read_text() == 'OLD'
    assert not list(tmp_path.glob('.*.tmp'))
