"""Enumerate photo inputs consistently for selection counts and detection."""

import os
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}


def collect_photo_inputs(sources, *, excluded_roots=(), should_cancel=None):
    paths, errors, seen = [], [], set()
    excluded = [Path(root).resolve() for root in excluded_roots]

    def cancelled():
        return should_cancel is not None and should_cancel()

    def is_excluded(path):
        resolved = path.resolve()
        return any(resolved == root or root in resolved.parents for root in excluded)

    def add(path):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(str(path))

    for source in sources:
        if cancelled():
            break
        path = Path(source).expanduser()
        try:
            if is_excluded(path):
                continue
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                add(path)
            elif path.is_dir():
                found = False

                def onerror(error):
                    errors.append(f"사진 폴더 읽기 오류: {error}")

                for directory, folders, files in os.walk(path, followlinks=False, onerror=onerror):
                    if cancelled():
                        break
                    base = Path(directory)
                    folders[:] = sorted(folder for folder in folders if not (
                        (base / folder).is_symlink() or is_excluded(base / folder)
                    ))
                    for name in sorted(files):
                        if cancelled():
                            break
                        candidate = base / name
                        if candidate.suffix.lower() in IMAGE_EXTENSIONS and not is_excluded(candidate):
                            add(candidate)
                            found = True
                if not found and not cancelled() and not errors:
                    errors.append(f"지원하는 사진이 없는 폴더: {path}")
            else:
                errors.append(f"지원하지 않거나 존재하지 않는 사진 경로: {path}")
        except OSError as error:
            errors.append(f"사진 입력 읽기 오류 ({path}): {error}")
    return paths, errors
