"""Allocate run folders and publish completed outputs without collisions."""

import os
import time
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QLockFile


def create_run_output_folder(base_folder, started_at=None):
    """Atomically reserve a timestamped folder, including for simultaneous runs."""
    base_folder = Path(base_folder)
    base_folder.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(started_at))
    suffix = 0
    while True:
        name = f"{timestamp}_{suffix}" if suffix else timestamp
        folder = base_folder / name
        try:
            folder.mkdir()
        except FileExistsError:
            suffix += 1
        else:
            return folder


@contextmanager
def _publication_lock(folder, is_cancelled):
    lock = QLockFile(str(folder / ".output-publish.lock"))
    # A slow filesystem must not let another live process steal this lock.
    # QLockFile still detects a lock left by a process that no longer exists.
    lock.setStaleLockTime(0)
    deadline = time.monotonic() + 10.0
    while True:
        if is_cancelled is not None and is_cancelled():
            raise RuntimeError("취소 요청으로 결과 저장을 중단했습니다.")
        if lock.tryLock(100):
            break
        if lock.error() != QLockFile.LockError.LockFailedError:
            raise RuntimeError("결과 폴더의 저장 잠금을 만들 수 없습니다. 쓰기 권한을 확인해 주세요.")
        if time.monotonic() >= deadline:
            raise RuntimeError("다른 작업이 결과를 저장 중입니다. 잠시 후 다시 시도해 주세요.")
    try:
        if is_cancelled is not None and is_cancelled():
            raise RuntimeError("취소 요청으로 결과 저장을 중단했습니다.")
        yield
    finally:
        lock.unlock()


def publish_output_files(staged_files, destination_names, is_cancelled=None):
    """Choose one free suffix and publish a completed file or photo pair.

    Staging and verification happen before this function; the lock covers only
    the final name selection and renames. Callers clean up unconsumed staging
    files on failure. A failed pair publication removes only its own outputs.
    """
    staged_files = [Path(path) for path in staged_files]
    names = [Path(name) for name in destination_names]
    if not staged_files or len(staged_files) != len(names):
        raise ValueError("저장할 결과 파일 목록을 확인해 주세요.")
    folder = staged_files[0].parent.resolve()
    if any(path.parent.resolve() != folder for path in staged_files):
        raise ValueError("임시 결과 파일은 같은 결과 폴더에 있어야 합니다.")
    if any(name.name != str(name) for name in names):
        raise ValueError("결과 파일 이름에는 폴더 경로를 사용할 수 없습니다.")

    with _publication_lock(folder, is_cancelled):
        suffix = 0
        while True:
            destinations = [
                folder / (f"{name.stem}_{suffix}{name.suffix}" if suffix else name.name)
                for name in names
            ]
            if not any(os.path.lexists(path) for path in destinations):
                break
            suffix += 1

        published = []
        try:
            for staged_file, destination in zip(staged_files, destinations):
                os.replace(staged_file, destination)
                published.append(destination)
        except Exception:
            for destination in published:
                destination.unlink(missing_ok=True)
            raise
    return destinations
