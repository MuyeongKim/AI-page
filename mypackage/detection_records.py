"""Photo/candidate records shared by detection, review and offline reports."""

import json
import math
from datetime import datetime
from pathlib import Path

import exifread

from mypackage import gps2

REVIEW_LABELS = {
    "unreviewed": "미확인", "person": "사람 맞음", "false_positive": "오탐", "hold": "보류",
}
MAX_RECORD_BYTES = 64 * 1024 * 1024


def read_photo_metadata(path):
    metadata = {"captured_at": None, "gps": None, "location_kind": "photo_gps", "warnings": []}
    try:
        with open(path, "rb") as stream:
            tags = exifread.process_file(stream, details=False)
        value = str(tags.get("EXIF DateTimeOriginal", ""))
        if value:
            captured = datetime.strptime(value, "%Y:%m:%d %H:%M:%S").isoformat()
            offset = str(tags.get("EXIF OffsetTimeOriginal", ""))
            metadata["captured_at"] = datetime.fromisoformat(captured + offset).isoformat()
        gps = gps2.extract_gps_data(path)
        if gps is not None:
            lat, lon = gps
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90
                    and -180 <= lon <= 180):
                raise ValueError("GPS 위경도가 유효하지 않습니다")
            metadata["gps"] = {"lat": lat, "lon": lon}
    except Exception as error:
        metadata["warnings"].append(f"촬영 메타데이터 확인 실패: {error}")
    return metadata


def append_result_candidates(photo, result):
    shape = getattr(result, "orig_shape", None)
    if shape is not None:
        photo["image_size"] = [int(shape[1]), int(shape[0])]
    boxes = result.boxes
    if boxes is None or not len(boxes.cls):
        return
    if not hasattr(boxes, "xyxy") or not hasattr(boxes, "conf") or not photo["image_size"]:
        photo["warnings"].append("후보 박스의 좌표·신뢰도·화면 크기를 읽지 못했습니다.")
        return
    width, height = photo["image_size"]
    for cls_id, coordinates, confidence in zip(boxes.cls, boxes.xyxy, boxes.conf):
        if int(cls_id) != 0:
            continue
        values = [float(value) for value in coordinates]
        score = float(confidence)
        if (not all(math.isfinite(value) for value in [*values, score])
                or len(values) != 4 or not 0 <= score <= 1):
            photo["warnings"].append("유효하지 않은 후보 박스를 기록에서 제외했습니다.")
            continue
        x1, y1, x2, y2 = values
        box = [max(0.0, min(width, x1)), max(0.0, min(height, y1)),
               max(0.0, min(width, x2)), max(0.0, min(height, y2))]
        if box[2] <= box[0] or box[3] <= box[1]:
            photo["warnings"].append("면적이 없는 후보 박스를 기록에서 제외했습니다.")
            continue
        photo["people"].append({
            "id": f"{photo['id']}-person-{len(photo['people']) + 1:03d}",
            "confidence": score, "box": box, "review": "unreviewed",
        })


def asset_path(folder, filename):
    """Accept only files within the selected run folder, including symlink resolution."""
    if not filename:
        return None
    if not isinstance(filename, str) or Path(filename).is_absolute():
        raise ValueError("결과 파일은 실행 폴더 안의 상대 경로여야 합니다.")
    folder = Path(folder).resolve()
    path = (folder / filename).resolve()
    if folder not in path.parents:
        raise ValueError("실행 폴더 밖의 결과 파일은 열 수 없습니다.")
    return path


def read_record_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("기록 파일이 허용 크기(64 MiB)를 넘었습니다.")
    with path.open(encoding="utf-8-sig") as stream:
        document = json.load(stream, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"유효하지 않은 숫자: {value}")
        ))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("지원하지 않는 기록 형식입니다.")
    return document


def load_detections(path):
    path = Path(path)
    document = read_record_json(path)
    photos = document.get("photos")
    if not isinstance(photos, list):
        raise ValueError("사진 기록 목록이 없습니다.")
    identities = set()
    for photo in photos:
        if not isinstance(photo, dict) or not isinstance(photo.get("people"), list):
            raise ValueError("잘못된 사진 기록입니다.")
        _validate_id(photo.get("id"), identities)
        if photo.get("status") not in {"completed", "failed", "cancelled"}:
            raise ValueError("잘못된 사진 처리 상태입니다.")
        for field in ("original_file", "detected_file"):
            asset_path(path.parent, photo.get(field))
        gps = photo.get("gps")
        if gps is not None:
            if not isinstance(gps, dict) or not _finite_number(gps.get("lat"), -90, 90) or not (
                    _finite_number(gps.get("lon"), -180, 180)):
                raise ValueError("촬영 위치가 유효하지 않습니다.")
        for candidate in photo["people"]:
            if not isinstance(candidate, dict):
                raise ValueError("잘못된 후보 기록입니다.")
            _validate_id(candidate.get("id"), identities)
            if candidate.get("review") not in REVIEW_LABELS:
                raise ValueError("잘못된 후보 확인 상태입니다.")
            size, box = photo.get("image_size"), candidate.get("box")
            if (not isinstance(size, list) or len(size) != 2
                    or not all(_finite_number(v, 1, 100000) for v in size)
                    or not isinstance(box, list) or len(box) != 4
                    or not all(_finite_number(v, 0, size[i % 2]) for i, v in enumerate(box))
                    or box[2] <= box[0] or box[3] <= box[1]
                    or not _finite_number(candidate.get("confidence"), 0, 1)):
                raise ValueError("후보 좌표·신뢰도가 유효하지 않습니다.")
    return document


def _finite_number(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and (
        math.isfinite(value) and low <= value <= high
    )


def _validate_id(value, identities):
    if not isinstance(value, str) or not value or value in identities:
        raise ValueError("기록 ID가 없거나 중복되었습니다.")
    identities.add(value)
