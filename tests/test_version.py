import json
import subprocess
import sys
from pathlib import Path

import pytest

from mypackage.version import (
    CURRENT_RELEASE,
    CURRENT_VERSION,
    assert_release_feed_matches_local,
    format_gui_changelog,
    release_feed_mismatches,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_release_drives_version_title_and_gui_changelog():
    changelog = format_gui_changelog()

    assert CURRENT_VERSION == CURRENT_RELEASE.version == "26.08.17"
    assert CURRENT_RELEASE.display_version in CURRENT_RELEASE.window_title
    assert "2026.08.17 V26.08.17 운영 안전성 개선" in changelog
    assert "미리보기를 최신 프레임 1장·20fps로 표시" in changelog
    assert "2026.08.08 안정성 및 사용성 개선" in changelog
    assert "README·라이선스 고지·결과 무결성 회귀 테스트 최신화" in changelog


def test_latest_version_feed_matches_local_release_metadata():
    with (PROJECT_ROOT / "latest_version.json").open(encoding="utf-8") as stream:
        feed = json.load(stream)

    assert release_feed_mismatches(feed) == ()
    assert_release_feed_matches_local(feed)


def test_release_feed_validation_reports_version_drift():
    mismatched_feed = {
        "version": "26.08.18",
        "release_date": CURRENT_RELEASE.release_date,
    }

    with pytest.raises(ValueError, match="version.*26\\.08\\.17.*26\\.08\\.18"):
        assert_release_feed_matches_local(mismatched_feed)


def test_check_version_supports_direct_script_import():
    script_path = PROJECT_ROOT / "mypackage" / "check_version.py"
    script_dir = script_path.parent
    smoke_code = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(script_dir)!r}); "
        f"runpy.run_path({str(script_path)!r}, run_name='direct_import_smoke')"
    )

    completed = subprocess.run(
        [sys.executable, "-c", smoke_code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
