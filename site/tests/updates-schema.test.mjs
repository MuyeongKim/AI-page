import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import {
  UpdateSchemaError,
  createEmptyFeed,
  createUpdateItem,
  patchUpdateItem,
  toPublicFeed,
  updateFeedItems,
  validateUpdatesFeed,
} from "../lib/updates-schema.js";


const NOW = new Date("2026-08-17T12:00:00.000Z");

function input(overrides = {}) {
  return {
    kind: "notice",
    status: "draft",
    title: "운영 안내",
    summary: "프로그램 운영 관련 안내입니다.",
    body: "본문은 일반 텍스트로만 작성합니다.",
    version: null,
    audiences: ["web", "desktop"],
    link_url: "https://github.com/MuyeongKim/AI-page",
    published_at: null,
    ...overrides,
  };
}

test("저장소 루트의 fallback feed가 공통 계약을 만족한다", async () => {
  const text = await readFile(new URL("../../site_updates.json", import.meta.url), "utf8");
  const feed = validateUpdatesFeed(JSON.parse(text));
  assert.equal(feed.schema_version, 1);
  assert.equal(feed.revision, 0);
});

test("생성·수정 계약은 서버 식별자와 시각을 유지하고 revision을 증가시킨다", () => {
  const draft = createUpdateItem(input(), { id: "update-1", now: NOW });
  assert.equal(draft.status, "draft");
  assert.equal(draft.published_at, null);

  const published = patchUpdateItem(draft, { status: "published" }, { now: NOW });
  assert.equal(published.published_at, NOW.toISOString());
  assert.equal(published.created_at, draft.created_at);

  const feed = updateFeedItems(createEmptyFeed(NOW), [published], { now: NOW });
  assert.equal(feed.revision, 1);
  assert.deepEqual(validateUpdatesFeed(feed), feed);
});

test("공개 계약은 게시 시각이 지난 published 항목만 반환하고 revision을 유지한다", () => {
  const published = createUpdateItem(input({ status: "published", published_at: null }), {
    id: "published",
    now: NOW,
  });
  const future = createUpdateItem(
    input({ status: "published", published_at: "2026-08-18T12:00:00Z" }),
    { id: "future", now: NOW },
  );
  const draft = createUpdateItem(input(), { id: "draft", now: NOW });
  const archived = createUpdateItem(input({ status: "archived" }), {
    id: "archived",
    now: NOW,
  });
  const feed = updateFeedItems(createEmptyFeed(NOW), [future, draft, archived, published], {
    now: NOW,
  });

  const publicFeed = toPublicFeed(feed, { now: NOW });
  assert.equal(publicFeed.revision, feed.revision);
  assert.deepEqual(publicFeed.items.map((item) => item.id), ["published"]);
});

test("HTML, 너무 긴 텍스트, 비HTTPS 링크와 중복 audience를 거부한다", () => {
  const invalidInputs = [
    input({ body: "<script>alert(1)</script>" }),
    input({ title: "가".repeat(121) }),
    input({ summary: "가".repeat(301) }),
    input({ body: "가".repeat(5_001) }),
    input({ link_url: "http://example.com" }),
    input({ link_url: "https://user:password@example.com" }),
    input({ link_url: "https://example.com\\@attacker.example" }),
    input({ audiences: ["web", "web"] }),
    input({ body: "정상처럼 보이는\u202E위장 문자열" }),
    input({ body: "UTF-8로 저장할 수 없는 \uD800 문자열" }),
  ];

  for (const invalid of invalidInputs) {
    assert.throws(
      () => createUpdateItem(invalid, { id: "invalid", now: NOW }),
      UpdateSchemaError,
    );
  }
});

test("updated_at이 created_at보다 빠른 외부 feed를 거부한다", () => {
  const item = createUpdateItem(input(), { id: "time-order", now: NOW });
  item.updated_at = "2026-08-16T12:00:00.000Z";
  assert.throws(
    () =>
      validateUpdatesFeed({
        schema_version: 1,
        revision: 1,
        updated_at: NOW.toISOString(),
        items: [item],
      }),
    UpdateSchemaError,
  );
});

test("존재하지 않는 날짜나 자동 보정되는 시각은 거부한다", () => {
  const invalidTimestamps = [
    "2026-02-30T12:00:00Z",
    "2026-01-01T24:00:00Z",
    "2026-01-01T12:60:00Z",
    "2026-01-01T12:00:60Z",
    "0000-01-01T12:00:00Z",
    "2026-01-01T12:00:00+24:00",
    "0001-01-01T00:00:00+23:59",
    "9999-12-31T23:59:59-23:59",
  ];

  for (const publishedAt of invalidTimestamps) {
    assert.throws(
      () =>
        createUpdateItem(
          input({ status: "published", published_at: publishedAt }),
          { id: "invalid-time", now: NOW },
        ),
      UpdateSchemaError,
    );
  }

  assert.equal(
    createUpdateItem(
      input({ status: "published", published_at: "2028-02-29T23:59:59+09:00" }),
      { id: "valid-leap-day", now: NOW },
    ).published_at,
    "2028-02-29T14:59:59.000Z",
  );
});

test("릴리스·다운로드 메타데이터를 관리자 payload에 섞을 수 없다", () => {
  assert.throws(
    () =>
      createUpdateItem(
        {
          ...input(),
          latest_version: "99.99.99",
          download: { url: "https://attacker.example/app.exe" },
        },
        { id: "unsafe", now: NOW },
      ),
    (error) =>
      error instanceof UpdateSchemaError && error.message.includes("허용되지 않은 필드"),
  );
});
