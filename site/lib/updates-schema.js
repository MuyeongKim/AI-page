export const UPDATE_KINDS = Object.freeze(["notice", "release", "maintenance"]);
export const UPDATE_STATUSES = Object.freeze(["draft", "published", "archived"]);
export const UPDATE_AUDIENCES = Object.freeze(["web", "desktop"]);

export const UPDATE_LIMITS = Object.freeze({
  title: 120,
  summary: 300,
  body: 5_000,
  version: 40,
  linkUrl: 2_048,
  items: 100,
});

const ITEM_KEYS = Object.freeze([
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
]);
const EDITABLE_KEYS = Object.freeze([
  "kind",
  "status",
  "title",
  "summary",
  "body",
  "version",
  "audiences",
  "link_url",
  "published_at",
]);
const ISO_8601_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,3})?(?:Z|[+-](\d{2}):(\d{2}))$/;
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/;
const CONTROL_CHARACTER_PATTERN = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;
const BIDI_CONTROL_PATTERN = /[\u202A-\u202E\u2066-\u2069]/;

export class UpdateSchemaError extends Error {
  constructor(message, details = undefined) {
    super(message);
    this.name = "UpdateSchemaError";
    this.details = details;
  }
}

function own(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function assertObject(value, field) {
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new UpdateSchemaError(`${field}는 객체여야 합니다.`);
  }
}

function assertOnlyKeys(value, allowedKeys, field) {
  const unexpected = Object.keys(value).filter((key) => !allowedKeys.includes(key));
  if (unexpected.length > 0) {
    throw new UpdateSchemaError(`${field}에 허용되지 않은 필드가 있습니다.`, unexpected);
  }
}

function characterLength(value) {
  return [...value].length;
}

function hasUnpairedSurrogate(value) {
  return [...value].some((character) => {
    const codepoint = character.codePointAt(0);
    return codepoint >= 0xD800 && codepoint <= 0xDFFF;
  });
}

function cleanText(value, field, maxLength, { allowNewlines = false } = {}) {
  if (typeof value !== "string") {
    throw new UpdateSchemaError(`${field}는 문자열이어야 합니다.`);
  }

  const cleaned = value.trim();
  const length = characterLength(cleaned);
  if (length === 0 || length > maxLength) {
    throw new UpdateSchemaError(`${field}는 1~${maxLength}자여야 합니다.`);
  }
  if (cleaned.includes("<") || cleaned.includes(">")) {
    throw new UpdateSchemaError(`${field}에는 HTML을 사용할 수 없습니다.`);
  }
  if (CONTROL_CHARACTER_PATTERN.test(cleaned)) {
    throw new UpdateSchemaError(`${field}에 허용되지 않은 제어 문자가 있습니다.`);
  }
  if (BIDI_CONTROL_PATTERN.test(cleaned)) {
    throw new UpdateSchemaError(`${field}에 방향 제어 문자를 사용할 수 없습니다.`);
  }
  if (hasUnpairedSurrogate(cleaned)) {
    throw new UpdateSchemaError(`${field}에 올바르지 않은 유니코드 문자가 있습니다.`);
  }
  if (!allowNewlines && /[\r\n]/.test(cleaned)) {
    throw new UpdateSchemaError(`${field}에는 줄바꿈을 사용할 수 없습니다.`);
  }
  return cleaned;
}

function cleanNullableText(value, field, maxLength) {
  if (value === null) {
    return null;
  }
  return cleanText(value, field, maxLength);
}

function cleanEnum(value, field, allowed) {
  if (!allowed.includes(value)) {
    throw new UpdateSchemaError(`${field} 값이 올바르지 않습니다.`, allowed);
  }
  return value;
}

function cleanAudiences(value) {
  if (!Array.isArray(value) || value.length === 0 || value.length > UPDATE_AUDIENCES.length) {
    throw new UpdateSchemaError("audiences는 web/desktop 중 하나 이상이어야 합니다.");
  }

  const unique = [...new Set(value)];
  if (unique.length !== value.length || unique.some((item) => !UPDATE_AUDIENCES.includes(item))) {
    throw new UpdateSchemaError("audiences 값이 올바르지 않거나 중복되었습니다.");
  }
  return UPDATE_AUDIENCES.filter((audience) => unique.includes(audience));
}

function cleanHttpsUrl(value) {
  if (value === null) {
    return null;
  }
  const cleaned = cleanText(value, "link_url", UPDATE_LIMITS.linkUrl);
  if (!cleaned.startsWith("https://") || cleaned.includes("\\")) {
    throw new UpdateSchemaError("link_url은 사용자 정보가 없는 HTTPS URL이어야 합니다.");
  }

  let parsed;
  try {
    parsed = new URL(cleaned);
  } catch {
    throw new UpdateSchemaError("link_url이 올바른 URL이 아닙니다.");
  }
  if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password) {
    throw new UpdateSchemaError("link_url은 사용자 정보가 없는 HTTPS URL이어야 합니다.");
  }
  return cleaned;
}

function cleanIso8601(value, field, { nullable = false } = {}) {
  if (nullable && value === null) {
    return null;
  }
  const match = typeof value === "string" ? ISO_8601_PATTERN.exec(value) : null;
  if (match === null) {
    throw new UpdateSchemaError(`${field}는 ISO 8601 날짜·시간이어야 합니다.`);
  }

  const [, yearText, monthText, dayText, hourText, minuteText, secondText, offsetHourText, offsetMinuteText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysByMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const validCalendarTime =
    year >= 1 &&
    month >= 1 &&
    month <= 12 &&
    day >= 1 &&
    day <= daysByMonth[month - 1] &&
    hour <= 23 &&
    minute <= 59 &&
    second <= 59 &&
    (offsetHourText === undefined ||
      (Number(offsetHourText) <= 23 && Number(offsetMinuteText) <= 59));
  if (!validCalendarTime || Number.isNaN(Date.parse(value))) {
    throw new UpdateSchemaError(`${field}는 ISO 8601 날짜·시간이어야 합니다.`);
  }
  const normalized = new Date(value).toISOString();
  const normalizedMatch = ISO_8601_PATTERN.exec(normalized);
  if (normalizedMatch === null || Number(normalizedMatch[1]) < 1) {
    throw new UpdateSchemaError(`${field}는 지원 범위 안의 날짜·시간이어야 합니다.`);
  }
  return normalized;
}

function toIso(now) {
  const date = now instanceof Date ? now : new Date(now);
  if (Number.isNaN(date.getTime())) {
    throw new UpdateSchemaError("현재 시각이 올바르지 않습니다.");
  }
  return date.toISOString();
}

export function validateUpdateItem(value) {
  assertObject(value, "item");
  assertOnlyKeys(value, ITEM_KEYS, "item");

  if (typeof value.id !== "string" || !ID_PATTERN.test(value.id)) {
    throw new UpdateSchemaError("id는 영문·숫자로 시작하는 1~100자 식별자여야 합니다.");
  }

  const status = cleanEnum(value.status, "status", UPDATE_STATUSES);
  const publishedAt = cleanIso8601(value.published_at, "published_at", { nullable: true });
  if (status === "published" && publishedAt === null) {
    throw new UpdateSchemaError("published 상태에는 published_at이 필요합니다.");
  }
  if (status === "draft" && publishedAt !== null) {
    throw new UpdateSchemaError("draft 상태의 published_at은 null이어야 합니다.");
  }

  const createdAt = cleanIso8601(value.created_at, "created_at");
  const updatedAt = cleanIso8601(value.updated_at, "updated_at");
  if (Date.parse(updatedAt) < Date.parse(createdAt)) {
    throw new UpdateSchemaError("updated_at은 created_at보다 빠를 수 없습니다.");
  }

  return {
    id: value.id,
    kind: cleanEnum(value.kind, "kind", UPDATE_KINDS),
    status,
    title: cleanText(value.title, "title", UPDATE_LIMITS.title),
    summary: cleanText(value.summary, "summary", UPDATE_LIMITS.summary),
    body: cleanText(value.body, "body", UPDATE_LIMITS.body, { allowNewlines: true }),
    version: cleanNullableText(value.version, "version", UPDATE_LIMITS.version),
    audiences: cleanAudiences(value.audiences),
    link_url: cleanHttpsUrl(value.link_url),
    published_at: publishedAt,
    created_at: createdAt,
    updated_at: updatedAt,
  };
}

export function validateUpdatesFeed(value) {
  assertObject(value, "feed");
  assertOnlyKeys(value, ["schema_version", "revision", "updated_at", "items"], "feed");
  if (value.schema_version !== 1) {
    throw new UpdateSchemaError("schema_version은 1이어야 합니다.");
  }
  if (!Number.isSafeInteger(value.revision) || value.revision < 0) {
    throw new UpdateSchemaError("revision은 0 이상의 안전한 정수여야 합니다.");
  }
  if (!Array.isArray(value.items) || value.items.length > UPDATE_LIMITS.items) {
    throw new UpdateSchemaError(`items는 최대 ${UPDATE_LIMITS.items}개인 배열이어야 합니다.`);
  }

  const items = value.items.map(validateUpdateItem);
  const ids = new Set(items.map((item) => item.id));
  if (ids.size !== items.length) {
    throw new UpdateSchemaError("items의 id가 중복되었습니다.");
  }

  return {
    schema_version: 1,
    revision: value.revision,
    updated_at: cleanIso8601(value.updated_at, "updated_at"),
    items,
  };
}

export function createEmptyFeed(now = new Date()) {
  return {
    schema_version: 1,
    revision: 0,
    updated_at: toIso(now),
    items: [],
  };
}

export function createUpdateItem(input, { id, now = new Date() }) {
  assertObject(input, "요청 본문");
  assertOnlyKeys(input, EDITABLE_KEYS, "요청 본문");
  const nowIso = toIso(now);
  const status = input.status ?? "draft";
  const publishedAt =
    status === "published" ? (input.published_at ?? nowIso) : (input.published_at ?? null);

  return validateUpdateItem({
    id,
    kind: input.kind ?? "notice",
    status,
    title: input.title,
    summary: input.summary,
    body: input.body,
    version: input.version ?? null,
    audiences: input.audiences ?? ["web", "desktop"],
    link_url: input.link_url ?? null,
    published_at: status === "draft" ? null : publishedAt,
    created_at: nowIso,
    updated_at: nowIso,
  });
}

export function patchUpdateItem(existing, changes, { now = new Date() } = {}) {
  const current = validateUpdateItem(existing);
  assertObject(changes, "changes");
  assertOnlyKeys(changes, EDITABLE_KEYS, "changes");
  if (Object.keys(changes).length === 0) {
    throw new UpdateSchemaError("changes에 수정할 필드가 필요합니다.");
  }

  const status = changes.status ?? current.status;
  let publishedAt = own(changes, "published_at") ? changes.published_at : current.published_at;
  if (status === "draft") {
    publishedAt = null;
  } else if (status === "published" && publishedAt === null) {
    publishedAt = toIso(now);
  }

  return validateUpdateItem({
    ...current,
    ...changes,
    id: current.id,
    status,
    published_at: publishedAt,
    created_at: current.created_at,
    updated_at: toIso(now),
  });
}

export function updateFeedItems(feed, items, { now = new Date() } = {}) {
  const current = validateUpdatesFeed(feed);
  return validateUpdatesFeed({
    schema_version: 1,
    revision: current.revision + 1,
    updated_at: toIso(now),
    items,
  });
}

export function toPublicFeed(feed, { now = new Date() } = {}) {
  const current = validateUpdatesFeed(feed);
  const nowMilliseconds = new Date(now).getTime();
  if (Number.isNaN(nowMilliseconds)) {
    throw new UpdateSchemaError("현재 시각이 올바르지 않습니다.");
  }

  return {
    ...current,
    items: current.items
      .filter(
        (item) =>
          item.status === "published" &&
          item.published_at !== null &&
          Date.parse(item.published_at) <= nowMilliseconds,
      )
      .sort((left, right) => Date.parse(right.published_at) - Date.parse(left.published_at)),
  };
}
