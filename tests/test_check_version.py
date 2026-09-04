import importlib

import pytest


def test_get_latest_version_skips_http_request_when_offline(monkeypatch):
    check_version = load_check_version()
    request_calls = []

    def fake_get(*args, **kwargs):
        request_calls.append((args, kwargs))
        raise check_version.requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(check_version, "has_internet_connection", lambda: False, raising=False)
    monkeypatch.setattr(check_version.requests, "get", fake_get)

    result = check_version.get_latest_version()

    assert result == "NO_CONNECTION"
    assert request_calls == []


def test_get_latest_version_requests_server_when_network_is_available(monkeypatch):
    check_version = load_check_version()
    request_calls = []

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "version": "26.0905",
                "download_url": None,
                "download": {
                    "status": "preparing",
                    "provider": "google_drive",
                    "platform": "Windows",
                    "filename": None,
                    "url": None,
                    "size_bytes": None,
                    "sha256": None,
                },
            }

    def fake_get(*args, **kwargs):
        request_calls.append((args, kwargs))
        return DummyResponse()

    monkeypatch.setattr(check_version, "has_internet_connection", lambda: True, raising=False)
    monkeypatch.setattr(check_version.requests, "get", fake_get)

    result = check_version.get_latest_version()

    assert result == "26.0905"
    assert len(request_calls) == 1


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("26.0905", (26, 9, 5)),
        ("26.09.05", (26, 9, 5)),
        ("26.08.17", (26, 8, 17)),
        ("26.08.25", (26, 8, 25)),
        ("26.4.9", (26, 4, 9)),
        ("26.1001", (26, 10, 1)),
        ("27.0101", (27, 1, 1)),
    ],
)
def test_version_tuple_normalizes_legacy_and_compact_calendar_versions(version, expected):
    assert load_check_version().version_to_tuple(version) == expected


@pytest.mark.parametrize(
    ("older", "newer"),
    [
        ("26.08.17", "26.0905"),
        ("26.08.25", "26.0905"),
        ("26.0904", "26.09.05"),
        ("26.0905", "26.0906"),
        ("26.0905", "26.09.06"),
        ("26.0930", "26.10.01"),
        ("26.12.31", "27.0101"),
    ],
)
def test_version_comparison_preserves_date_order_across_formats(older, newer):
    compare = load_check_version().version_to_tuple
    assert compare(older) < compare(newer)


@pytest.mark.parametrize(
    ("remote_version", "should_notify"),
    [
        ("26.08.17", False),
        ("26.08.25", False),
        ("26.0905", False),
        ("26.09.05", False),
        ("26.0906", True),
        ("26.10.01", True),
        ("27.0101", True),
    ],
)
def test_update_notice_only_appears_for_a_later_calendar_version(
    monkeypatch, remote_version, should_notify
):
    check_version = load_check_version()
    messages = []
    monkeypatch.setattr(check_version, "CURRENT_VERSION", "26.0905")
    monkeypatch.setattr(check_version, "get_latest_version", lambda: remote_version)
    monkeypatch.setattr(check_version, "show_message", lambda *args: messages.append(args))

    check_version.main()

    assert bool(messages) is should_notify


def load_check_version():
    return importlib.import_module("mypackage.check_version")
