import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mypackage.version import CURRENT_RELEASE
from scripts.export_release import (
    ReleaseFeedError,
    build_ready_download,
    build_release_feed,
    current_release_changelog,
    export_release,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = PROJECT_ROOT / "scripts" / "export_release.py"


GOOGLE_DRIVE_URL = "https://drive.google.com/file/d/example/view"


def _write_artifact(tmp_path: Path, content: bytes = b"real windows artifact") -> Path:
    artifact = tmp_path / "AI-detection.exe"
    artifact.write_bytes(content)
    return artifact


def test_current_feed_is_generated_from_current_release_and_marks_download_preparing():
    feed_path = PROJECT_ROOT / "latest_version.json"
    with feed_path.open(encoding="utf-8") as stream:
        actual = json.load(stream)

    expected = build_release_feed(actual)

    assert actual == expected
    assert actual["version"] == CURRENT_RELEASE.version == "26.0905"
    assert actual["release_date"] == CURRENT_RELEASE.release_date == "2026-09-05"
    assert actual["changelog"] == current_release_changelog()
    assert actual["download_url"] is None
    assert actual["download"] == {
        "status": "preparing",
        "provider": "google_drive",
        "platform": "Windows",
        "filename": None,
        "url": None,
        "size_bytes": None,
        "sha256": None,
    }


def test_ready_metadata_is_calculated_from_actual_file(tmp_path):
    content = b"MZ\x00\x01actual executable bytes\xff"
    artifact = _write_artifact(tmp_path, content)

    download = build_ready_download(artifact, GOOGLE_DRIVE_URL)

    assert download == {
        "status": "ready",
        "provider": "google_drive",
        "platform": "Windows",
        "filename": "AI-detection.exe",
        "url": GOOGLE_DRIVE_URL,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def test_ready_google_drive_download_is_preserved_for_same_release(tmp_path):
    artifact = _write_artifact(tmp_path)
    ready_download = build_ready_download(artifact, GOOGLE_DRIVE_URL)
    existing = {
        "version": CURRENT_RELEASE.version,
        "download_url": None,
        "download": ready_download,
    }

    feed = build_release_feed(existing)

    assert feed["download_url"] == GOOGLE_DRIVE_URL
    assert feed["download"] == ready_download


@pytest.mark.parametrize("old_version", ["26.08.17", "26.08.25", "26.0904"])
def test_old_release_download_is_not_reused_for_new_release(tmp_path, old_version):
    artifact = _write_artifact(tmp_path)
    existing = {
        "version": old_version,
        "download_url": GOOGLE_DRIVE_URL,
        "download": build_ready_download(artifact, GOOGLE_DRIVE_URL),
    }

    feed = build_release_feed(existing)

    assert feed["download_url"] is None
    assert feed["download"]["status"] == "preparing"
    assert feed["download"]["url"] is None


def test_ready_download_rejects_non_google_drive_url(tmp_path):
    artifact = _write_artifact(tmp_path)
    with pytest.raises(ReleaseFeedError, match="Google Drive HTTPS"):
        build_ready_download(artifact, "https://example.com/AI-detection.exe")


def test_ready_download_rejects_missing_file(tmp_path):
    with pytest.raises(ReleaseFeedError, match="존재하지 않거나 일반 파일"):
        build_ready_download(tmp_path / "missing.exe", GOOGLE_DRIVE_URL)


def test_ready_download_rejects_empty_file(tmp_path):
    artifact = _write_artifact(tmp_path, b"")

    with pytest.raises(ReleaseFeedError, match="빈 배포 파일"):
        build_ready_download(artifact, GOOGLE_DRIVE_URL)


def test_check_mode_reports_drift_without_modifying_file(tmp_path, capsys):
    feed_path = tmp_path / "latest_version.json"
    stale_feed = {
        "version": "0.0.0",
        "release_date": "2000-01-01",
        "download_url": "https://stayup-ai.com",
        "changelog": ["오래된 변경 내용"],
    }
    feed_path.write_text(json.dumps(stale_feed, ensure_ascii=False), encoding="utf-8")
    before = feed_path.read_bytes()

    matches = export_release(feed_path, check=True)

    assert matches is False
    assert feed_path.read_bytes() == before
    assert "CURRENT_RELEASE 기준" in capsys.readouterr().err


def test_export_mode_replaces_stale_feed_with_safe_current_release(tmp_path):
    artifact = _write_artifact(tmp_path)
    feed_path = tmp_path / "latest_version.json"
    feed_path.write_text(
        json.dumps(
            {
                "version": "26.08.16",
                "download_url": GOOGLE_DRIVE_URL,
                "download": build_ready_download(artifact, GOOGLE_DRIVE_URL),
            }
        ),
        encoding="utf-8",
    )

    already_current = export_release(feed_path, check=False)

    assert already_current is False
    with feed_path.open(encoding="utf-8") as stream:
        generated = json.load(stream)
    assert generated["version"] == CURRENT_RELEASE.version
    assert generated["download_url"] is None
    assert generated["download"]["status"] == "preparing"
    assert export_release(feed_path, check=True) is True


def test_cli_builds_ready_feed_from_file_and_url_and_can_check_it(tmp_path):
    content = b"release artifact verified by CLI"
    artifact = _write_artifact(tmp_path, content)
    feed_path = tmp_path / "latest_version.json"

    generated = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--output",
            str(feed_path),
            "--download-file",
            str(artifact),
            "--download-url",
            GOOGLE_DRIVE_URL,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert generated.returncode == 0, generated.stderr
    with feed_path.open(encoding="utf-8") as stream:
        feed = json.load(stream)
    assert feed["download_url"] == GOOGLE_DRIVE_URL
    assert feed["download"]["filename"] == artifact.name
    assert feed["download"]["size_bytes"] == len(content)
    assert feed["download"]["sha256"] == hashlib.sha256(content).hexdigest()

    checked = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--check",
            "--output",
            str(feed_path),
            "--download-file",
            str(artifact),
            "--download-url",
            GOOGLE_DRIVE_URL,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize(
    "incomplete_options",
    [
        ("--download-file", "artifact.exe"),
        ("--download-url", GOOGLE_DRIVE_URL),
    ],
)
def test_cli_requires_download_file_and_url_together(tmp_path, incomplete_options):
    completed = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--output",
            str(tmp_path / "latest_version.json"),
            *incomplete_options,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert "반드시 함께 지정" in completed.stderr


def test_export_script_check_succeeds_for_repository_feed():
    completed = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "CURRENT_RELEASE와 일치합니다" in completed.stdout
