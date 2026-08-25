import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mypackage import gui, notices


NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def _item(item_id="desktop-current", **overrides):
    item = {
        "id": item_id,
        "kind": "notice",
        "status": "published",
        "title": "온라인 안내",
        "summary": "중요한 운영 안내입니다.",
        "body": "본문은 검증된 일반 텍스트로 표시됩니다.",
        "version": None,
        "audiences": ["desktop"],
        "link_url": "https://example.com/notices/1",
        "published_at": "2026-08-17T09:00:00Z",
        "created_at": "2026-08-16T09:00:00Z",
        "updated_at": "2026-08-17T09:00:00Z",
    }
    item.update(overrides)
    return item


def _feed(items=None, revision=3):
    return {
        "schema_version": 1,
        "revision": revision,
        "updated_at": "2026-08-17T10:00:00Z",
        "items": list(items or []),
    }


def _encoded(feed):
    return json.dumps(feed, ensure_ascii=False).encode("utf-8")


@pytest.fixture(scope="session")
def qapp():
    application = QApplication.instance() or QApplication([])
    yield application
    application.processEvents()


def test_only_published_current_desktop_items_are_returned_in_newest_order():
    feed = notices.validate_notice_feed(
        _feed(
            [
                _item("older", published_at="2026-08-16T09:00:00Z"),
                _item("web-only", audiences=["web"]),
                _item("draft", status="draft", published_at=None),
                _item("future", published_at="2026-08-18T09:00:00Z"),
                _item("newer", kind="release", version="V26.08.17"),
                _item("archived", status="archived"),
            ]
        )
    )

    result = notices.desktop_published_items(feed, NOW)

    assert [item.id for item in result] == ["newer", "older"]


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("kind", "promotion"),
        ("status", "public"),
        ("audiences", ["desktop", "desktop"]),
        ("link_url", "http://example.com/notices/1"),
        ("published_at", None),
        ("status", "draft"),
        ("created_at", "2026-08-17T09:00:00"),
        ("created_at", "9999-12-31T23:59:59-23:59"),
        ("updated_at", "2026-08-15T09:00:00Z"),
        ("title", "두 줄\n제목"),
        ("title", "잘못된 유니코드 \ud800"),
        ("title", "<script>"),
        ("id", "dot.is-not-allowed"),
        ("title", "제" * 121),
        ("summary", "요" * 301),
        ("body", "본" * 5_001),
        ("version", "V" * 41),
    ],
)
def test_item_contract_rejects_invalid_values(field, invalid_value):
    item = _item()
    item[field] = invalid_value

    with pytest.raises(notices.NoticeValidationError):
        notices.validate_notice_feed(_feed([item]))


def test_feed_contract_rejects_boolean_revision_and_unknown_keys():
    boolean_revision = _feed(revision=True)
    with pytest.raises(notices.NoticeValidationError):
        notices.validate_notice_feed(boolean_revision)

    unknown_key = _feed()
    unknown_key["unexpected"] = "value"
    with pytest.raises(notices.NoticeValidationError):
        notices.validate_notice_feed(unknown_key)


def test_text_fields_follow_shared_trim_and_length_contract():
    feed = notices.validate_notice_feed(
        _feed(
            [
                _item(
                    "a" * 100,
                    title=f"  {'제' * 120}  ",
                    summary=f"  {'요' * 300}  ",
                    body=f"\n{'본' * 5_000}\n",
                    version=f"  {'V' * 40}  ",
                )
            ]
        )
    )

    item = feed.items[0]
    assert item.title == "제" * 120
    assert item.summary == "요" * 300
    assert item.body == "본" * 5_000
    assert item.version == "V" * 40


def test_repository_feed_is_a_shared_contract_fixture():
    repository_feed = Path(__file__).resolve().parents[1] / "site_updates.json"

    feed = notices.parse_notice_feed(repository_feed.read_bytes())

    assert feed.revision >= 0


def test_json_decoder_rejects_duplicate_keys_and_oversized_payload():
    duplicate_revision = (
        b'{"schema_version":1,"revision":1,"revision":2,'
        b'"updated_at":"2026-08-17T10:00:00Z","items":[]}'
    )
    with pytest.raises(notices.NoticeValidationError, match="duplicate JSON key"):
        notices.parse_notice_feed(duplicate_revision)

    oversized = b" " * (notices.MAX_NOTICE_RESPONSE_BYTES + 1)
    with pytest.raises(notices.NoticeValidationError, match="invalid size"):
        notices.parse_notice_feed(oversized)

    deeply_nested = ("[" * 1_200 + "0" + "]" * 1_200).encode()
    # Python's JSON recursion threshold varies by runtime version, but the
    # excessively nested non-object feed must always be rejected.
    with pytest.raises(notices.NoticeValidationError):
        notices.parse_notice_feed(deeply_nested)


def test_network_failure_or_invalid_remote_uses_last_valid_cache(tmp_path):
    cache_path = tmp_path / "user-data" / "site_updates.json"
    cached_feed = notices.validate_notice_feed(_feed([_item("cached")], revision=7))
    notices.write_notice_cache(cached_feed, cache_path)

    disconnected = notices.resolve_notice_result(None, cache_path, now=NOW)
    invalid_remote = notices.resolve_notice_result(b"{}", cache_path, now=NOW)

    assert disconnected.source == notices.NOTICE_SOURCE_CACHE
    assert disconnected.revision == 7
    assert [item.id for item in disconnected.items] == ["cached"]
    assert invalid_remote == disconnected


def test_cache_round_trip_preserves_millisecond_timestamps(tmp_path):
    cache_path = tmp_path / "site_updates.json"
    feed = notices.validate_notice_feed(
        _feed(
            [
                _item(
                    "milliseconds",
                    published_at="2026-08-17T09:00:00.123Z",
                    created_at="2026-08-16T09:00:00.456Z",
                    updated_at="2026-08-17T09:00:00.789Z",
                )
            ]
        )
    )

    notices.write_notice_cache(feed, cache_path)
    restored = notices.read_notice_cache(cache_path)

    assert restored is not None
    assert restored.revision == feed.revision
    assert restored.items[0].published_at == feed.items[0].published_at
    assert b".123Z" in cache_path.read_bytes()


def test_valid_remote_replaces_cache_and_is_returned_even_if_cache_write_fails(
    tmp_path, monkeypatch
):
    cache_path = tmp_path / "site_updates.json"
    old_feed = notices.validate_notice_feed(_feed([_item("old")], revision=4))
    notices.write_notice_cache(old_feed, cache_path)
    old_bytes = cache_path.read_bytes()

    remote_payload = _encoded(_feed([_item("new")], revision=5))
    original_replace = notices.os.replace

    def fail_replace(_source, _destination):
        raise OSError("disk unavailable")

    monkeypatch.setattr(notices.os, "replace", fail_replace)
    result = notices.resolve_notice_result(remote_payload, cache_path, now=NOW)

    assert result.source == notices.NOTICE_SOURCE_REMOTE
    assert result.revision == 5
    assert [item.id for item in result.items] == ["new"]
    assert cache_path.read_bytes() == old_bytes
    assert list(cache_path.parent.glob(".*.tmp")) == []

    monkeypatch.setattr(notices.os, "replace", original_replace)
    notices.write_notice_cache(notices.parse_notice_feed(remote_payload), cache_path)
    assert notices.read_notice_cache(cache_path).revision == 5


def test_lower_remote_revision_does_not_replace_newer_cache(tmp_path):
    cache_path = tmp_path / "site_updates.json"
    cached_feed = notices.validate_notice_feed(_feed([_item("newer")], revision=8))
    notices.write_notice_cache(cached_feed, cache_path)
    cached_bytes = cache_path.read_bytes()

    result = notices.resolve_notice_result(
        _encoded(_feed([_item("older")], revision=7)),
        cache_path,
        now=NOW,
    )

    assert result.source == notices.NOTICE_SOURCE_CACHE
    assert result.revision == 8
    assert [item.id for item in result.items] == ["newer"]
    assert cache_path.read_bytes() == cached_bytes


def test_missing_or_corrupt_cache_is_a_quiet_empty_result(tmp_path):
    cache_path = tmp_path / "site_updates.json"
    missing = notices.resolve_notice_result(None, cache_path, now=NOW)
    assert missing == notices.NoticeLoadResult(
        revision=0,
        items=(),
        source=notices.NOTICE_SOURCE_EMPTY,
    )

    cache_path.write_bytes(b"not-json")
    corrupt = notices.resolve_notice_result(None, cache_path, now=NOW)
    assert corrupt == missing


class _MemorySettings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


def test_gui_shows_non_modal_news_tab_and_marks_revision_seen(qapp, monkeypatch):
    settings = _MemorySettings()
    monkeypatch.setattr(gui, "QSettings", lambda *_arguments: settings)
    window = gui.Ui_MainWindow()
    try:
        assert not window.infoTabs.isTabVisible(window.online_notice_tab_index)
        feed = notices.validate_notice_feed(
            _feed(
                [
                    _item(
                        "gui-news",
                        kind="release",
                        title="V26 온라인 안내",
                        version="V26.08.17",
                    )
                ],
                revision=9,
            )
        )
        result = notices.NoticeLoadResult(
            revision=feed.revision,
            items=notices.desktop_published_items(feed, NOW),
            source=notices.NOTICE_SOURCE_REMOTE,
        )

        window._display_online_notices(result)

        assert window.infoTabs.isTabVisible(window.online_notice_tab_index)
        assert window.infoTabs.tabText(window.online_notice_tab_index) == "온라인 소식 · 새 글"
        rendered = window.plainTextEdit_online_notice.toPlainText()
        assert "[업데이트] V26 온라인 안내" in rendered
        assert "대상 버전: V26.08.17" in rendered
        assert "https://example.com/notices/1" in rendered

        window.infoTabs.setCurrentIndex(window.online_notice_tab_index)
        assert settings.values[gui.NOTICE_SETTINGS_REVISION_KEY] == 9
        assert window.infoTabs.tabText(window.online_notice_tab_index) == "온라인 소식"

        window._display_online_notices(
            notices.NoticeLoadResult(
                revision=10,
                items=(),
                source=notices.NOTICE_SOURCE_REMOTE,
            )
        )
        assert not window.infoTabs.isTabVisible(window.online_notice_tab_index)
    finally:
        window._closing_without_confirmation = True
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_gui_labels_cached_news_as_last_known_content(qapp, monkeypatch):
    settings = _MemorySettings()
    monkeypatch.setattr(gui, "QSettings", lambda *_arguments: settings)
    window = gui.Ui_MainWindow()
    try:
        feed = notices.validate_notice_feed(_feed([_item("cached-gui")], revision=11))
        window._display_online_notices(
            notices.NoticeLoadResult(
                revision=feed.revision,
                items=notices.desktop_published_items(feed, NOW),
                source=notices.NOTICE_SOURCE_CACHE,
            )
        )

        rendered = window.plainTextEdit_online_notice.toPlainText()
        assert "마지막으로 저장된 내용을 표시합니다" in rendered
    finally:
        window._closing_without_confirmation = True
        window.close()
        window.deleteLater()
        qapp.processEvents()
