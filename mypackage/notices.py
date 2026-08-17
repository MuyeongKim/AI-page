"""Fetch, validate, cache, and filter the public online-news feed."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QStandardPaths, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


NOTICE_FEED_URL = (
    "https://raw.githubusercontent.com/MuyeongKim/AI-page/content/site_updates.json"
)
NOTICE_SCHEMA_VERSION = 1
NOTICE_REQUEST_TIMEOUT_MS = 5_000
MAX_NOTICE_RESPONSE_BYTES = 256 * 1024
MAX_NOTICE_ITEMS = 100

NOTICE_SOURCE_REMOTE = "remote"
NOTICE_SOURCE_CACHE = "cache"
NOTICE_SOURCE_EMPTY = "empty"

_FEED_KEYS = {"schema_version", "revision", "updated_at", "items"}
_ITEM_KEYS = {
    "id",
    "kind",
    "status",
    "title",
    "summary",
    "body",
    "version",
    "audiences",
    "link_url",
    "published_at",
    "created_at",
    "updated_at",
}
_NOTICE_KINDS = {"notice", "release", "maintenance"}
_NOTICE_STATUSES = {"draft", "published", "archived"}
_NOTICE_AUDIENCES = {"web", "desktop"}
_NOTICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")
_ISO8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$"
)
_BIDI_CONTROL_CHARACTERS = {
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}


class NoticeValidationError(ValueError):
    """Raised when an online-news feed does not match the public contract."""


@dataclass(frozen=True)
class NoticeItem:
    id: str
    kind: str
    status: str
    title: str
    summary: str
    body: str
    version: str | None
    audiences: tuple[str, ...]
    link_url: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NoticeFeed:
    revision: int
    updated_at: datetime
    items: tuple[NoticeItem, ...]


@dataclass(frozen=True)
class NoticeLoadResult:
    revision: int
    items: tuple[NoticeItem, ...]
    source: str


def default_notice_cache_path() -> Path:
    """Return the per-user application-data cache location."""
    app_data = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not app_data:
        app_data = str(Path.home() / ".stayup-ai")
    return Path(app_data) / "online_news" / "site_updates.json"


def _require_exact_keys(value: object, expected: set[str], context: str) -> dict:
    if type(value) is not dict:
        raise NoticeValidationError(f"{context} must be an object")
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise NoticeValidationError(
            f"{context} has invalid keys (missing={missing}, extra={extra})"
        )
    return value


def _validate_text(
    value: object,
    context: str,
    *,
    max_chars: int,
    allow_empty: bool = False,
    multiline: bool = False,
) -> str:
    if type(value) is not str:
        raise NoticeValidationError(f"{context} must be a string")
    normalized = value.strip()
    if len(normalized) > max_chars:
        raise NoticeValidationError(f"{context} is too long")
    if not allow_empty and not normalized:
        raise NoticeValidationError(f"{context} must not be empty")
    if not multiline and ("\r" in normalized or "\n" in normalized):
        raise NoticeValidationError(f"{context} must be one line")
    if "<" in normalized or ">" in normalized:
        raise NoticeValidationError(f"{context} contains an HTML delimiter")
    for character in normalized:
        codepoint = ord(character)
        allowed_control = character == "\t" or (
            multiline and character in {"\r", "\n"}
        )
        if (codepoint < 32 and not allowed_control) or codepoint == 127:
            raise NoticeValidationError(f"{context} contains a control character")
        if 0xD800 <= codepoint <= 0xDFFF:
            raise NoticeValidationError(f"{context} contains an unpaired surrogate")
        if character in _BIDI_CONTROL_CHARACTERS:
            raise NoticeValidationError(f"{context} contains a bidi control character")
    return normalized


def _parse_timestamp(value: object, context: str) -> datetime:
    text = _validate_text(value, context, max_chars=40)
    if not _ISO8601_PATTERN.fullmatch(text):
        raise NoticeValidationError(f"{context} must be an ISO 8601 timestamp")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise NoticeValidationError(f"{context} is not a valid timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NoticeValidationError(f"{context} must include a timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise NoticeValidationError(f"{context} is not a valid timestamp") from error


def _parse_optional_timestamp(value: object, context: str) -> datetime | None:
    if value is None:
        return None
    return _parse_timestamp(value, context)


def _validate_link(value: object, context: str) -> str | None:
    if value is None:
        return None
    link = _validate_text(value, context, max_chars=2_048)
    if not link.startswith("https://") or "\\" in link:
        raise NoticeValidationError(f"{context} must use https")
    try:
        parsed = urlsplit(link)
        _ = parsed.port
    except ValueError as error:
        raise NoticeValidationError(f"{context} is not a valid URL") from error
    if parsed.scheme != "https" or not parsed.hostname:
        raise NoticeValidationError(f"{context} must be an absolute https URL")
    if parsed.username is not None or parsed.password is not None:
        raise NoticeValidationError(f"{context} must not contain credentials")
    return link


def _validate_item(value: object, index: int) -> NoticeItem:
    context = f"items[{index}]"
    item = _require_exact_keys(value, _ITEM_KEYS, context)

    item_id = _validate_text(item["id"], f"{context}.id", max_chars=100)
    if not _NOTICE_ID_PATTERN.fullmatch(item_id):
        raise NoticeValidationError(f"{context}.id has an invalid format")

    kind = _validate_text(item["kind"], f"{context}.kind", max_chars=20)
    if kind not in _NOTICE_KINDS:
        raise NoticeValidationError(f"{context}.kind is unsupported")

    status = _validate_text(item["status"], f"{context}.status", max_chars=20)
    if status not in _NOTICE_STATUSES:
        raise NoticeValidationError(f"{context}.status is unsupported")

    audiences_value = item["audiences"]
    if type(audiences_value) is not list or not 1 <= len(audiences_value) <= 2:
        raise NoticeValidationError(f"{context}.audiences must contain one or two values")
    if any(type(audience) is not str for audience in audiences_value):
        raise NoticeValidationError(f"{context}.audiences must contain strings")
    audiences = tuple(audiences_value)
    if len(set(audiences)) != len(audiences) or set(audiences) - _NOTICE_AUDIENCES:
        raise NoticeValidationError(f"{context}.audiences contains an invalid value")

    version_value = item["version"]
    if version_value is None:
        version = None
    else:
        version = _validate_text(version_value, f"{context}.version", max_chars=40)

    published_at = _parse_optional_timestamp(
        item["published_at"], f"{context}.published_at"
    )
    if status == "published" and published_at is None:
        raise NoticeValidationError(
            f"{context}.published_at is required for published items"
        )
    if status == "draft" and published_at is not None:
        raise NoticeValidationError(
            f"{context}.published_at must be null for draft items"
        )

    created_at = _parse_timestamp(item["created_at"], f"{context}.created_at")
    updated_at = _parse_timestamp(item["updated_at"], f"{context}.updated_at")
    if updated_at < created_at:
        raise NoticeValidationError(f"{context}.updated_at precedes created_at")

    return NoticeItem(
        id=item_id,
        kind=kind,
        status=status,
        title=_validate_text(item["title"], f"{context}.title", max_chars=120),
        summary=_validate_text(item["summary"], f"{context}.summary", max_chars=300),
        body=_validate_text(
            item["body"], f"{context}.body", max_chars=5_000, multiline=True
        ),
        version=version,
        audiences=audiences,
        link_url=_validate_link(item["link_url"], f"{context}.link_url"),
        published_at=published_at,
        created_at=created_at,
        updated_at=updated_at,
    )


def validate_notice_feed(value: object) -> NoticeFeed:
    """Validate a decoded feed and return an immutable representation."""
    feed = _require_exact_keys(value, _FEED_KEYS, "feed")
    if type(feed["schema_version"]) is not int:
        raise NoticeValidationError("schema_version must be an integer")
    if feed["schema_version"] != NOTICE_SCHEMA_VERSION:
        raise NoticeValidationError("schema_version is unsupported")

    revision = feed["revision"]
    if type(revision) is not int or not 0 <= revision <= 9_007_199_254_740_991:
        raise NoticeValidationError("revision must be a non-negative safe integer")

    items_value = feed["items"]
    if type(items_value) is not list or len(items_value) > MAX_NOTICE_ITEMS:
        raise NoticeValidationError("items must be a bounded array")

    items = tuple(_validate_item(item, index) for index, item in enumerate(items_value))
    item_ids = [item.id for item in items]
    if len(set(item_ids)) != len(item_ids):
        raise NoticeValidationError("item ids must be unique")

    return NoticeFeed(
        revision=revision,
        updated_at=_parse_timestamp(feed["updated_at"], "updated_at"),
        items=items,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise NoticeValidationError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise NoticeValidationError(f"invalid JSON constant: {value}")


def parse_notice_feed(data: bytes) -> NoticeFeed:
    """Decode a size-bounded UTF-8 JSON document with duplicate-key rejection."""
    if type(data) is not bytes:
        raise NoticeValidationError("feed payload must be bytes")
    if not data or len(data) > MAX_NOTICE_RESPONSE_BYTES:
        raise NoticeValidationError("feed payload has an invalid size")
    try:
        decoded = data.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise NoticeValidationError("feed payload is not valid UTF-8 JSON") from error
    return validate_notice_feed(value)


def _format_timestamp(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def notice_feed_to_dict(feed: NoticeFeed) -> dict:
    """Convert a validated feed to its canonical cache representation."""
    items = []
    for item in feed.items:
        items.append(
            {
                "id": item.id,
                "kind": item.kind,
                "status": item.status,
                "title": item.title,
                "summary": item.summary,
                "body": item.body,
                "version": item.version,
                "audiences": list(item.audiences),
                "link_url": item.link_url,
                "published_at": (
                    _format_timestamp(item.published_at)
                    if item.published_at is not None
                    else None
                ),
                "created_at": _format_timestamp(item.created_at),
                "updated_at": _format_timestamp(item.updated_at),
            }
        )
    return {
        "schema_version": NOTICE_SCHEMA_VERSION,
        "revision": feed.revision,
        "updated_at": _format_timestamp(feed.updated_at),
        "items": items,
    }


def write_notice_cache(feed: NoticeFeed, cache_path: Path | str) -> None:
    """Atomically replace the last-known-good per-user cache."""
    destination = Path(cache_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            notice_feed_to_dict(feed),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    if len(payload) > MAX_NOTICE_RESPONSE_BYTES:
        raise OSError("validated notice cache exceeds the cache size limit")

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def read_notice_cache(cache_path: Path | str) -> NoticeFeed | None:
    """Read and revalidate the cache, returning None for any unusable cache."""
    try:
        with Path(cache_path).open("rb") as cache_file:
            payload = cache_file.read(MAX_NOTICE_RESPONSE_BYTES + 1)
        return parse_notice_feed(payload)
    except (OSError, NoticeValidationError):
        return None


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    return now.astimezone(timezone.utc)


def desktop_published_items(
    feed: NoticeFeed, now: datetime | None = None
) -> tuple[NoticeItem, ...]:
    """Return published desktop items whose publication time has arrived."""
    current_time = _normalize_now(now)
    items = (
        item
        for item in feed.items
        if item.status == "published"
        and "desktop" in item.audiences
        and item.published_at is not None
        and item.published_at <= current_time
    )
    return tuple(
        sorted(items, key=lambda item: (item.published_at, item.updated_at), reverse=True)
    )


def resolve_notice_result(
    remote_data: bytes | None,
    cache_path: Path | str | None = None,
    *,
    now: datetime | None = None,
) -> NoticeLoadResult:
    """Prefer a valid remote feed and silently fall back to valid cache or empty."""
    destination = Path(cache_path) if cache_path is not None else default_notice_cache_path()
    cached_feed = read_notice_cache(destination)

    if remote_data is not None:
        try:
            remote_feed = parse_notice_feed(remote_data)
        except NoticeValidationError:
            remote_feed = None
        if remote_feed is not None:
            if cached_feed is not None and remote_feed.revision < cached_feed.revision:
                return NoticeLoadResult(
                    revision=cached_feed.revision,
                    items=desktop_published_items(cached_feed, now),
                    source=NOTICE_SOURCE_CACHE,
                )
            try:
                write_notice_cache(remote_feed, destination)
            except OSError:
                # Fresh, validated content is still safe to display if persistence fails.
                pass
            return NoticeLoadResult(
                revision=remote_feed.revision,
                items=desktop_published_items(remote_feed, now),
                source=NOTICE_SOURCE_REMOTE,
            )

    if cached_feed is not None:
        return NoticeLoadResult(
            revision=cached_feed.revision,
            items=desktop_published_items(cached_feed, now),
            source=NOTICE_SOURCE_CACHE,
        )
    return NoticeLoadResult(revision=0, items=(), source=NOTICE_SOURCE_EMPTY)


class OnlineNoticeLoader(QObject):
    """Load the feed through Qt's asynchronous network stack."""

    loaded = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        cache_path: Path | str | None = None,
        network_manager: QNetworkAccessManager | None = None,
    ):
        super().__init__(parent)
        self.cache_path = (
            Path(cache_path) if cache_path is not None else default_notice_cache_path()
        )
        self._network_manager = network_manager or QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None
        self._buffer = bytearray()
        self._too_large = False
        self._closed = False

    def refresh(self) -> None:
        if self._closed or self._reply is not None:
            return

        request = QNetworkRequest(QUrl(NOTICE_FEED_URL))
        request.setTransferTimeout(NOTICE_REQUEST_TIMEOUT_MS)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"User-Agent", b"StayUpAI-Desktop")

        self._buffer.clear()
        self._too_large = False
        try:
            reply = self._network_manager.get(request)
        except Exception:
            self.loaded.emit(resolve_notice_result(None, self.cache_path))
            return
        self._reply = reply
        reply.readyRead.connect(self._read_available_data)
        reply.finished.connect(self._finish_request)

    def _read_available_data(self) -> None:
        reply = self._reply
        if reply is None or self._too_large:
            return
        chunk = bytes(reply.readAll())
        if len(self._buffer) + len(chunk) > MAX_NOTICE_RESPONSE_BYTES:
            self._too_large = True
            self._buffer.clear()
            reply.abort()
            return
        self._buffer.extend(chunk)

    def _finish_request(self) -> None:
        reply = self._reply
        if reply is None:
            return
        self._read_available_data()

        status_value = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )
        try:
            status_code = int(status_value)
        except (TypeError, ValueError):
            status_code = 0
        succeeded = (
            not self._too_large
            and reply.error() == QNetworkReply.NetworkError.NoError
            and status_code == 200
        )
        remote_data = bytes(self._buffer) if succeeded else None

        self._reply = None
        self._buffer.clear()
        reply.deleteLater()
        if not self._closed:
            self.loaded.emit(resolve_notice_result(remote_data, self.cache_path))

    def cancel(self) -> None:
        """Abort an in-flight request when its window is closing."""
        self._closed = True
        reply = self._reply
        self._reply = None
        self._buffer.clear()
        if reply is None:
            return
        try:
            reply.readyRead.disconnect(self._read_available_data)
            reply.finished.disconnect(self._finish_request)
        except (RuntimeError, TypeError):
            pass
        reply.abort()
        reply.deleteLater()
