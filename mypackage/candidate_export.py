"""Portable photo candidates for STAY UP; never export absolute source paths."""

import base64
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath
from uuid import UUID, uuid4

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QLockFile, Qt
from PySide6.QtGui import QImageReader

from mypackage.detection_records import asset_path, load_detections
from mypackage.run_report import write_json_file
from mypackage.version import CURRENT_VERSION

EXPORT_FILENAME = "stayup-ai-candidates.json"
MAX_EXPORT_BYTES = 16 * 1024 * 1024
MAX_CANDIDATES = 5000
MAX_THUMBNAIL_BYTES = 32 * 1024
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")


def _thumbnail(path):
    if path is None or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return None
    reader = QImageReader(str(path))
    size = reader.size()
    if bytes(reader.format()) != b"jpeg" or not size.isValid() or max(size.width(), size.height()) > 4096:
        return None
    reader.setAutoTransform(True)
    reader.setScaledSize(size.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return None
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "JPEG", 65) or data.size() > MAX_THUMBNAIL_BYTES:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(bytes(data)).decode("ascii")


def export_photo_candidates(record_path, destination):
    record_path, destination = Path(record_path).resolve(), Path(destination).resolve()
    if (destination == record_path or destination.suffix.lower() != ".json"
            or destination.name in {"detections.json", "live_events.json", "run_summary.json"}):
        raise ValueError("원본 기록과 다른 JSON 파일로 저장해 주세요.")
    lock = QLockFile(str(record_path) + ".edit.lock")
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise OSError("다른 창이 후보 기록을 수정 중입니다. 잠시 후 다시 내보내세요.")
    try:
        document = load_detections(record_path)
        status = document.get("status", "completed")
        if status not in {"completed", "partial", "cancelled", "failed"}:
            raise ValueError("분석이 끝난 사진 기록만 내보낼 수 있습니다.")
        candidates = []
        for photo in document["photos"]:
            for filename in [photo.get("original_file"), photo.get("detected_file"),
                             *(c.get("thumbnail_file") for c in photo["people"])]:
                if asset_path(record_path.parent, filename) == destination:
                    raise ValueError("원본·탐지본·후보 이미지를 덮어쓸 수 없습니다.")
            if photo["status"] != "completed":
                continue
            captured = photo.get("captured_at")
            if captured is not None:
                if (not isinstance(captured, str) or len(captured) > 40
                        or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)?", captured)):
                    raise ValueError("사진 촬영 시각을 확인해 주세요.")
                instant = datetime.fromisoformat(captured.replace("Z", "+00:00"))
                offset = instant.utcoffset()
                if offset is not None and abs(offset.total_seconds()) > 14 * 3600:
                    raise ValueError("촬영 시각의 시간대 범위를 확인해 주세요.")
            filename = PureWindowsPath(str(photo.get("source", ""))).name[:120]
            for candidate in photo["people"]:
                if not all(ID_PATTERN.fullmatch(value) for value in [photo["id"], candidate["id"]]):
                    raise ValueError("후보·사진 ID 형식을 확인해 주세요.")
                if not all(type(v) is int for v in photo["image_size"]):
                    raise ValueError("원본 이미지 크기는 정수 픽셀이어야 합니다.")
                candidates.append({
                    "id": candidate["id"], "photoId": photo["id"], "file": filename,
                    "capturedAt": captured, "gps": photo.get("gps"),
                    "locationKind": "photo_gps", "confidence": candidate["confidence"],
                    "review": candidate["review"], "box": candidate["box"],
                    "imageSize": photo["image_size"],
                    "thumbnail": _thumbnail(asset_path(record_path.parent,
                                                       candidate.get("thumbnail_file"))),
                })
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError("한 파일은 후보 5,000건까지 내보낼 수 있습니다.")
        run_id = str(UUID(document["run_id"])) if document.get("run_id") else str(uuid4())
        counts = {"status": status, "photoCount": len(document["photos"]),
                  "completedCount": sum(p["status"] == "completed" for p in document["photos"]),
                  "failedCount": sum(p["status"] != "completed" for p in document["photos"])}
        digest = hashlib.sha256(json.dumps([counts, candidates], sort_keys=True,
                                          ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        previous = document.get("stayup_export", {})
        revision = previous.get("revision", 0)
        if type(revision) is not int or not 0 <= revision < 2**53 - 1:
            raise ValueError("내보내기 리비전이 유효하지 않습니다.")
        revision += revision == 0 or previous.get("digest") != digest
        payload = {"format": "stayup-ai-candidates", "version": 1,
                   "generatedAt": datetime.now().astimezone().isoformat(),
                   "app": {"name": "STAY UP AI", "version": CURRENT_VERSION},
                   "run": {"id": run_id, "revision": revision, **counts}, "candidates": candidates}
        if len(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")) + 1 > MAX_EXPORT_BYTES:
            raise ValueError("후보 파일이 16 MiB를 넘습니다. 사진 묶음을 나누어 분석해 주세요.")
        document["run_id"] = run_id
        document["stayup_export"] = {"revision": revision, "digest": digest}
        # Reserve identity/revision before publishing. A failed export can be
        # retried with the same revision; earlier files stay intact.
        write_json_file(record_path, document)
        write_json_file(destination, payload)
        return payload
    finally:
        lock.unlock()
