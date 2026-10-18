"""Bounded candidate thumbnails from the model's orientation-correct original pixels."""

import math
from pathlib import Path

import cv2

from mypackage.run_report import write_bytes_file


def candidate_thumbnail(image, box):
    if image is None or image.ndim != 3 or image.size == 0:
        raise ValueError("후보 원본 프레임이 없습니다.")
    if len(box) != 4 or not all(math.isfinite(value) for value in box):
        raise ValueError("후보 좌표가 유효하지 않습니다.")
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        raise ValueError("후보 영역이 비어 있습니다.")
    height, width = image.shape[:2]
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w, half_h = max(96, (x2 - x1) * 3) / 2, max(96, (y2 - y1) * 3) / 2
    left, top = max(0, math.floor(cx - half_w)), max(0, math.floor(cy - half_h))
    right, bottom = min(width, math.ceil(cx + half_w)), min(height, math.ceil(cy + half_h))
    cropped = image[top:bottom, left:right]
    if cropped.size == 0:
        raise ValueError("후보가 사진 화면 밖에 있습니다.")
    scale = 480 / max(cropped.shape[:2])
    preview = cv2.resize(cropped, (max(1, round(cropped.shape[1] * scale)),
                                  max(1, round(cropped.shape[0] * scale))))
    ok, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise OSError("후보 확대 이미지를 만들지 못했습니다.")
    return encoded.tobytes()


def save_candidate_thumbnail(folder, candidate, image):
    identifier = candidate["id"]
    if not identifier or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_"
                             for character in identifier):
        raise ValueError("잘못된 후보 이미지 ID입니다.")
    relative = Path("candidates") / f"{identifier}.jpg"
    destination = Path(folder) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_file(destination, candidate_thumbnail(image, candidate["box"]))
    return relative.as_posix()
