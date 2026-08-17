"""로컬 릴리스 정보를 공개 업데이트 피드로 생성하거나 검증한다.

기본 실행은 ``latest_version.json``을 갱신하고, ``--check``는 파일을
수정하지 않은 채 현재 ``mypackage.version.CURRENT_RELEASE``와 일치하는지
검증한다. 다운로드 메타데이터는 같은 버전에서만 보존하므로 새 버전이
준비되기 전에 이전 설치 파일이 최신 버전으로 잘못 노출되지 않는다.

실제 Windows 배포 파일을 공개할 때는 파일 경로와 Google Drive URL을 함께
전달한다. 크기와 SHA-256은 파일에서 직접 계산하므로 수동으로 입력하지 않는다.

.. code-block:: console

   python scripts/export_release.py \\
       --download-file dist/AI-detection.exe \\
       --download-url https://drive.google.com/file/d/FILE_ID/view
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "latest_version.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mypackage.version import CURRENT_RELEASE, ReleaseInfo  # noqa: E402


DOWNLOAD_PROVIDER = "google_drive"
DOWNLOAD_PLATFORM = "Windows"
DOWNLOAD_STATUSES = frozenset({"preparing", "ready", "unavailable"})
HASH_CHUNK_SIZE = 1024 * 1024
GOOGLE_DRIVE_HOSTS = frozenset(
    {
        "docs.google.com",
        "drive.google.com",
        "drive.usercontent.google.com",
    }
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class ReleaseFeedError(ValueError):
    """릴리스 피드를 안전하게 생성할 수 없을 때 발생한다."""


def _normalise_date(value: str) -> str:
    """GUI 이력의 점 표기 날짜를 피드의 ISO 날짜와 비교할 수 있게 한다."""
    return value.replace(".", "-")


def current_release_changelog(release: ReleaseInfo = CURRENT_RELEASE) -> list[str]:
    """현재 릴리스 날짜에 해당하는 변경 내용만 공개 피드용으로 반환한다."""
    items = [
        item
        for section in release.changelog
        if _normalise_date(section.date) == release.release_date
        for item in section.items
    ]
    if not items:
        raise ReleaseFeedError(
            f"현재 릴리스 날짜({release.release_date})와 일치하는 변경 이력이 없습니다."
        )
    return items


def _default_download() -> dict[str, object]:
    """설치 파일을 아직 공개하지 않은 릴리스의 안전한 기본 상태."""
    return {
        "status": "preparing",
        "provider": DOWNLOAD_PROVIDER,
        "platform": DOWNLOAD_PLATFORM,
        "filename": None,
        "url": None,
        "size_bytes": None,
        "sha256": None,
    }


def _is_google_drive_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in GOOGLE_DRIVE_HOSTS


def build_ready_download(download_file: Path, download_url: str) -> dict[str, object]:
    """실제 배포 파일을 읽어 검증 가능한 ready 메타데이터를 만든다."""
    if not _is_google_drive_url(download_url):
        raise ReleaseFeedError("download URL은 허용된 Google Drive HTTPS 주소여야 합니다.")
    if not download_file.is_file():
        raise ReleaseFeedError(f"배포 파일이 존재하지 않거나 일반 파일이 아닙니다: {download_file}")

    filename = download_file.name
    if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename:
        raise ReleaseFeedError(f"배포 파일명이 올바르지 않습니다: {filename!r}")

    digest = hashlib.sha256()
    size_bytes = 0
    try:
        with download_file.open("rb") as stream:
            while chunk := stream.read(HASH_CHUNK_SIZE):
                digest.update(chunk)
                size_bytes += len(chunk)
    except OSError as error:
        raise ReleaseFeedError(f"배포 파일을 읽을 수 없습니다: {error}") from error

    if size_bytes == 0:
        raise ReleaseFeedError(f"빈 배포 파일은 공개할 수 없습니다: {download_file}")

    return {
        "status": "ready",
        "provider": DOWNLOAD_PROVIDER,
        "platform": DOWNLOAD_PLATFORM,
        "filename": filename,
        "url": download_url,
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
    }


def _normalise_download(value: Mapping[str, object]) -> dict[str, object]:
    """Google Drive 다운로드 상태를 검증하고 고정된 공개 스키마로 정리한다."""
    status = value.get("status")
    if status not in DOWNLOAD_STATUSES:
        allowed = ", ".join(sorted(DOWNLOAD_STATUSES))
        raise ReleaseFeedError(f"download.status는 {allowed} 중 하나여야 합니다: {status!r}")

    provider = value.get("provider", DOWNLOAD_PROVIDER)
    if provider != DOWNLOAD_PROVIDER:
        raise ReleaseFeedError(f"download.provider는 {DOWNLOAD_PROVIDER!r}여야 합니다.")

    platform = value.get("platform")
    if platform != DOWNLOAD_PLATFORM:
        raise ReleaseFeedError(f"download.platform은 {DOWNLOAD_PLATFORM!r}여야 합니다.")

    filename = value.get("filename")
    url = value.get("url")
    size_bytes = value.get("size_bytes")
    sha256 = value.get("sha256")

    if status == "ready":
        if (
            not isinstance(filename, str)
            or not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
        ):
            raise ReleaseFeedError("ready 상태의 download.filename은 파일명만 포함해야 합니다.")
        if not isinstance(url, str) or not _is_google_drive_url(url):
            raise ReleaseFeedError(
                "ready 상태의 download.url은 허용된 Google Drive HTTPS 주소여야 합니다."
            )
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes <= 0:
            raise ReleaseFeedError("ready 상태의 download.size_bytes는 양의 정수여야 합니다.")
        if not isinstance(sha256, str) or SHA256_PATTERN.fullmatch(sha256) is None:
            raise ReleaseFeedError("ready 상태의 download.sha256은 64자리 16진수여야 합니다.")
        sha256 = sha256.lower()
    elif any(item is not None for item in (filename, url, size_bytes, sha256)):
        raise ReleaseFeedError(
            f"{status} 상태에서는 download.filename/url/size_bytes/sha256이 "
            "모두 null이어야 합니다."
        )

    return {
        "status": status,
        "provider": provider,
        "platform": platform,
        "filename": filename,
        "url": url,
        "size_bytes": size_bytes,
        "sha256": sha256,
    }


def _download_for_release(
    existing_feed: Mapping[str, object],
    release: ReleaseInfo,
) -> dict[str, object]:
    """같은 버전의 유효한 다운로드 상태만 이어받는다."""
    if existing_feed.get("version") != release.version:
        return _default_download()

    existing_download = existing_feed.get("download")
    if existing_download is None:
        return _default_download()
    if not isinstance(existing_download, Mapping):
        raise ReleaseFeedError("download는 객체이거나 생략되어야 합니다.")
    return _normalise_download(existing_download)


def build_release_feed(
    existing_feed: Mapping[str, object] | None = None,
    release: ReleaseInfo = CURRENT_RELEASE,
    download_override: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """로컬 단일 원본과 기존 배포 상태를 결합한 공개 피드를 만든다."""
    existing_feed = existing_feed or {}
    download = (
        _normalise_download(download_override)
        if download_override is not None
        else _download_for_release(existing_feed, release)
    )
    legacy_download_url = download["url"] if download["status"] == "ready" else None

    return {
        "version": release.version,
        "release_date": release.release_date,
        "download_url": legacy_download_url,
        "download": download,
        "changelog": current_release_changelog(release),
    }


def _read_feed(path: Path, *, missing_ok: bool) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except FileNotFoundError:
        if missing_ok:
            return {}
        raise ReleaseFeedError(f"릴리스 피드가 없습니다: {path}") from None
    except json.JSONDecodeError as error:
        raise ReleaseFeedError(f"릴리스 피드 JSON이 올바르지 않습니다: {error}") from error
    except OSError as error:
        raise ReleaseFeedError(f"릴리스 피드를 읽을 수 없습니다: {error}") from error

    if not isinstance(value, dict):
        raise ReleaseFeedError("릴리스 피드 최상위 값은 JSON 객체여야 합니다.")
    return value


def _serialise(feed: Mapping[str, object]) -> str:
    return json.dumps(feed, ensure_ascii=False, indent=2) + "\n"


def _write_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary_path = Path(stream.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _diff(actual: Mapping[str, object], expected: Mapping[str, object], path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            _serialise(actual).splitlines(keepends=True),
            _serialise(expected).splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (CURRENT_RELEASE 기준)",
        )
    )


def export_release(
    path: Path,
    *,
    check: bool,
    download_file: Path | None = None,
    download_url: str | None = None,
) -> bool:
    """피드를 검증하거나 갱신하고, 이미 일치하면 True를 반환한다."""
    if (download_file is None) != (download_url is None):
        raise ReleaseFeedError("--download-file과 --download-url은 반드시 함께 지정해야 합니다.")
    if download_file is not None and download_file.resolve() == path.resolve():
        raise ReleaseFeedError("배포 파일과 latest_version.json 출력 경로는 달라야 합니다.")

    download_override = (
        build_ready_download(download_file, download_url)
        if download_file is not None and download_url is not None
        else None
    )
    existing_feed = _read_feed(path, missing_ok=not check)
    expected_feed = build_release_feed(existing_feed, download_override=download_override)
    matches = existing_feed == expected_feed

    if check:
        if not matches:
            print(_diff(existing_feed, expected_feed, path), file=sys.stderr, end="")
        return matches

    if not matches:
        _write_atomically(path, _serialise(expected_feed))
    return matches


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CURRENT_RELEASE에서 latest_version.json을 생성하거나 검증합니다.",
        epilog=(
            "ready 피드 생성 예:\n"
            "  python scripts/export_release.py \\\n"
            "      --download-file dist/AI-detection.exe \\\n"
            "      --download-url https://drive.google.com/file/d/FILE_ID/view\n\n"
            "파일명·크기·SHA-256은 실제 파일에서 계산되므로 수동 입력하지 않습니다."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="파일을 수정하지 않고 CURRENT_RELEASE와의 일치 여부만 검사합니다.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"출력할 피드 경로입니다. 기본값: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--download-file",
        type=Path,
        help=(
            "ready로 공개할 실제 Windows 배포 파일입니다. 크기·SHA-256·파일명을 "
            "직접 계산하며 --download-url과 함께 사용해야 합니다."
        ),
    )
    parser.add_argument(
        "--download-url",
        help="배포 파일의 Google Drive HTTPS 주소입니다. --download-file과 함께 사용합니다.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        already_current = export_release(
            args.output,
            check=args.check,
            download_file=args.download_file,
            download_url=args.download_url,
        )
    except ReleaseFeedError as error:
        print(f"릴리스 피드 오류: {error}", file=sys.stderr)
        return 2

    if args.check:
        if already_current:
            print(f"릴리스 피드가 CURRENT_RELEASE와 일치합니다: {args.output}")
            return 0
        print("릴리스 피드가 CURRENT_RELEASE와 일치하지 않습니다.", file=sys.stderr)
        return 1

    if already_current:
        print(f"릴리스 피드가 이미 최신 상태입니다: {args.output}")
    else:
        print(f"릴리스 피드를 갱신했습니다: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
