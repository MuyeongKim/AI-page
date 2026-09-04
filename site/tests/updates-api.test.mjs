import assert from "node:assert/strict";
import { test } from "node:test";

import adminUpdatesFunction, { handleAdminUpdates } from "../api/admin/updates.js";
import publicUpdatesFunction, { handlePublicUpdates } from "../api/updates.js";
import { createAdminSession } from "../lib/admin-auth.js";
import { createEmptyFeed, createUpdateItem, updateFeedItems } from "../lib/updates-schema.js";


const NOW = new Date("2026-08-17T12:00:00.000Z");
const ORIGIN = "https://updates.example";
const ENV = {
  ADMIN_SESSION_SECRET: "test-session-secret-that-is-at-least-32-bytes",
  GITHUB_CONTENT_TOKEN: "github-secret-token-never-returned",
  GITHUB_CONTENT_OWNER: "MuyeongKim",
  GITHUB_CONTENT_REPO: "AI-page",
  GITHUB_CONTENT_BRANCH: "content",
};

test("Vercel Web Standard 기본 export는 fetch 함수로 Response를 반환한다", async () => {
  assert.equal(typeof publicUpdatesFunction.fetch, "function");
  assert.equal(typeof adminUpdatesFunction.fetch, "function");

  const publicResponse = await publicUpdatesFunction.fetch(
    new Request(`${ORIGIN}/api/updates`, { method: "POST" }),
  );
  const adminResponse = await adminUpdatesFunction.fetch(
    new Request(`${ORIGIN}/api/admin/updates`, { method: "OPTIONS" }),
  );
  assert.equal(publicResponse instanceof Response, true);
  assert.equal(adminResponse instanceof Response, true);
  assert.equal(publicResponse.status, 405);
  assert.equal(adminResponse.status, 405);
});

function jsonResponse(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function createGitHubFake({ branches = ["content", "main"], files = {} } = {}) {
  const state = {
    branches: new Set(branches),
    files: new Map(),
    requests: [],
    conflict: false,
    conflictStatus: 409,
    sequence: 1,
  };

  for (const [branch, feed] of Object.entries(files)) {
    state.files.set(branch, { feed, sha: `sha-${state.sequence++}` });
  }

  const fetchImpl = async (url, init = {}) => {
    const parsed = new URL(url);
    const method = init.method ?? "GET";
    state.requests.push({ url: parsed, method, init });

    const branchMatch = parsed.pathname.match(/\/branches\/(.+)$/);
    if (method === "GET" && branchMatch) {
      const branch = decodeURIComponent(branchMatch[1]);
      return state.branches.has(branch)
        ? jsonResponse({ name: branch })
        : jsonResponse({ message: "Not Found" }, 404);
    }

    if (!parsed.pathname.endsWith("/contents/site_updates.json")) {
      return jsonResponse({ message: "Not Found" }, 404);
    }

    if (method === "GET") {
      const branch = parsed.searchParams.get("ref");
      const stored = state.files.get(branch);
      if (!state.branches.has(branch) || !stored) {
        return jsonResponse({ message: "Not Found" }, 404);
      }
      return jsonResponse({
        type: "file",
        encoding: "base64",
        content: Buffer.from(`${JSON.stringify(stored.feed)}\n`).toString("base64"),
        sha: stored.sha,
      });
    }

    if (method === "PUT") {
      if (state.conflict) {
        return jsonResponse({ message: "sha does not match" }, state.conflictStatus);
      }
      const body = JSON.parse(init.body);
      if (!state.branches.has(body.branch)) {
        return jsonResponse({ message: "Not Found" }, 404);
      }
      const existing = state.files.get(body.branch);
      if (existing && body.sha !== existing.sha) {
        return jsonResponse({ message: "sha does not match" }, 409);
      }
      const feed = JSON.parse(Buffer.from(body.content, "base64").toString("utf8"));
      const sha = `sha-${state.sequence++}`;
      state.files.set(body.branch, { feed, sha });
      return jsonResponse({ content: { sha }, commit: { sha: `commit-${sha}` } });
    }

    return jsonResponse({ message: "Method Not Allowed" }, 405);
  };

  return { state, fetchImpl };
}

function adminRequest(method, body = undefined, { origin = ORIGIN } = {}) {
  const session = createAdminSession(ENV, { now: NOW, nonce: Buffer.alloc(18, 9) });
  const headers = {
    Cookie: session.cookie.split(";", 1)[0],
    Origin: origin,
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  return new Request(`${ORIGIN}/api/admin/updates`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function updateInput(overrides = {}) {
  return {
    kind: "notice",
    status: "published",
    title: "새 업데이트",
    summary: "웹과 데스크톱에 함께 표시됩니다.",
    body: "관리자가 작성한 일반 텍스트 공지입니다.",
    version: null,
    audiences: ["web", "desktop"],
    link_url: "https://github.com/MuyeongKim/AI-page",
    published_at: null,
    ...overrides,
  };
}

test("관리자 API는 content 브랜치의 site_updates.json만 CRUD한다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  const dependencies = {
    env: ENV,
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "update-created",
  };

  const createdResponse = await handleAdminUpdates(adminRequest("POST", updateInput()), dependencies);
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json();
  assert.equal(created.item.id, "update-created");
  assert.equal(created.item.published_at, NOW.toISOString());
  assert.equal(created.feed.revision, 1);

  const put = github.state.requests.find((request) => request.method === "PUT");
  assert.equal(put.url.pathname.endsWith("/contents/site_updates.json"), true);
  assert.equal(put.url.pathname.includes("latest_version"), false);
  const putBody = JSON.parse(put.init.body);
  assert.equal(putBody.branch, "content");
  assert.equal(putBody.sha, "sha-1");
  assert.equal(put.init.headers.Authorization, `Bearer ${ENV.GITHUB_CONTENT_TOKEN}`);
  assert.equal(
    github.state.requests.every((request) => request.init.signal instanceof AbortSignal),
    true,
  );
  assert.equal(JSON.stringify(created).includes(ENV.GITHUB_CONTENT_TOKEN), false);

  const listedResponse = await handleAdminUpdates(adminRequest("GET"), dependencies);
  assert.equal(listedResponse.status, 200);
  assert.equal((await listedResponse.json()).items.length, 1);

  const patchedResponse = await handleAdminUpdates(
    adminRequest("PATCH", {
      id: "update-created",
      changes: { status: "archived", summary: "보관된 공지입니다." },
      expected_revision: 1,
    }),
    dependencies,
  );
  assert.equal(patchedResponse.status, 200);
  assert.equal((await patchedResponse.json()).item.status, "archived");

  const deletedResponse = await handleAdminUpdates(
    adminRequest("DELETE", { id: "update-created", expected_revision: 2 }),
    dependencies,
  );
  assert.equal(deletedResponse.status, 200);
  const deleted = await deletedResponse.json();
  assert.equal(deleted.deleted_id, "update-created");
  assert.equal(deleted.feed.items.length, 0);
});

test("두 편집 화면의 순차 저장에서 오래된 수정과 삭제는 최신 내용을 덮어쓰지 않는다", async () => {
  const original = createUpdateItem(updateInput({ title: "원래 제목" }), { id: "shared", now: NOW });
  const feed = updateFeedItems(createEmptyFeed(NOW), [original], { now: NOW });
  const github = createGitHubFake({ files: { content: feed } });
  const dependencies = { env: ENV, fetchImpl: github.fetchImpl, now: () => NOW };
  const first = await handleAdminUpdates(adminRequest("PATCH", {
    id: "shared", changes: { title: "먼저 저장한 제목" }, expected_revision: feed.revision,
  }), dependencies);
  assert.equal(first.status, 200);
  const firstPayload = await first.json();
  const writesBeforeConflict = github.state.requests.filter((request) => request.method === "PUT").length;

  for (const [method, body] of [
    ["PATCH", { id: "shared", changes: { title: "원래 제목", body: "다른 화면에서 수정한 본문" }, expected_revision: feed.revision }],
    ["DELETE", { id: "shared", expected_revision: feed.revision }],
  ]) {
    const response = await handleAdminUpdates(adminRequest(method, body), dependencies);
    assert.equal(response.status, 409);
    assert.equal((await response.json()).error.code, "UPDATE_REVISION_CONFLICT");
  }
  assert.equal(github.state.requests.filter((request) => request.method === "PUT").length, writesBeforeConflict);
  assert.equal(github.state.files.get("content").feed.items[0].title, "먼저 저장한 제목");

  const retry = await handleAdminUpdates(adminRequest("PATCH", {
    id: "shared", changes: { title: "먼저 저장한 제목", body: "비교 후 반영한 본문" },
    expected_revision: firstPayload.feed.revision,
  }), dependencies);
  assert.equal(retry.status, 200);
  assert.equal((await retry.json()).item.body, "비교 후 반영한 본문");
});

test("수정과 삭제에서 리비전 누락 또는 올바르지 않은 리비전은 쓰기 전에 거부한다", async () => {
  const original = createUpdateItem(updateInput(), { id: "shared", now: NOW });
  const feed = updateFeedItems(createEmptyFeed(NOW), [original], { now: NOW });
  const github = createGitHubFake({ files: { content: feed } });
  const dependencies = { env: ENV, fetchImpl: github.fetchImpl, now: () => NOW };
  for (const method of ["PATCH", "DELETE"]) {
    for (const revision of [undefined, null, -1, 1.5, "1"]) {
      const body = { id: "shared", ...(method === "PATCH" ? { changes: { title: "수정" } } : {}) };
      if (revision !== undefined) body.expected_revision = revision;
      assert.equal((await handleAdminUpdates(adminRequest(method, body), dependencies)).status, 400);
    }
  }
  assert.equal(github.state.requests.some((request) => request.method === "PUT"), false);
});

test("UTF-8 바이트가 큰 스키마 허용 본문도 관리자 API가 저장한다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(
    adminRequest("POST", updateInput({ body: "😀".repeat(5_000) })),
    {
      env: ENV,
      fetchImpl: github.fetchImpl,
      now: () => NOW,
      createId: () => "unicode-limit",
    },
  );

  assert.equal(response.status, 201);
  const payload = await response.json();
  assert.equal([...payload.item.body].length, 5_000);
});

test("현재 blob SHA 충돌은 409로 반환한다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  github.state.conflict = true;

  const response = await handleAdminUpdates(adminRequest("POST", updateInput()), {
    env: ENV,
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "conflict",
  });
  assert.equal(response.status, 409);
  assert.equal((await response.json()).error.code, "BLOB_SHA_CONFLICT");
});

test("파일 최초 생성 경합의 GitHub 422 SHA 오류도 409로 정규화한다", async () => {
  const github = createGitHubFake();
  github.state.conflict = true;
  github.state.conflictStatus = 422;

  const response = await handleAdminUpdates(adminRequest("POST", updateInput()), {
    env: ENV,
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "create-conflict",
  });
  assert.equal(response.status, 409);
  assert.equal((await response.json()).error.code, "BLOB_SHA_CONFLICT");
});

test("content 파일 최초 생성은 main fallback revision을 이어서 쓴다", async () => {
  const mainFeed = updateFeedItems(createEmptyFeed(NOW), [], { now: NOW });
  const github = createGitHubFake({ files: { main: mainFeed } });

  const response = await handleAdminUpdates(adminRequest("POST", updateInput()), {
    env: ENV,
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "from-main-fallback",
  });
  assert.equal(response.status, 201);
  const payload = await response.json();
  assert.equal(payload.feed.revision, mainFeed.revision + 1);
  const put = github.state.requests.find((request) => request.method === "PUT");
  assert.equal(JSON.parse(put.init.body).branch, "content");
  assert.equal(Object.hasOwn(JSON.parse(put.init.body), "sha"), false);
});

test("content 브랜치가 없으면 쓰기를 거부하고 main으로 쓰지 않는다", async () => {
  const github = createGitHubFake({ branches: ["main"], files: { main: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(adminRequest("POST", updateInput()), {
    env: ENV,
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "must-not-write",
  });

  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, "CONTENT_BRANCH_MISSING");
  assert.equal(github.state.requests.some((request) => request.method === "PUT"), false);
});

test("쓰기 브랜치를 main으로 설정해도 명확히 거부한다", async () => {
  const github = createGitHubFake({ files: { main: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(adminRequest("POST", updateInput()), {
    env: { ...ENV, GITHUB_CONTENT_BRANCH: "main" },
    fetchImpl: github.fetchImpl,
    now: () => NOW,
    createId: () => "must-not-write-main",
  });

  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, "GITHUB_NOT_CONFIGURED");
  assert.equal(github.state.requests.some((request) => request.method === "PUT"), false);
});

test("공개 GET은 content 실패 시 main을 읽기 전용 fallback으로 사용하고 게시물만 반환한다", async () => {
  const published = createUpdateItem(updateInput(), { id: "published", now: NOW });
  const draft = createUpdateItem(updateInput({ status: "draft", published_at: null }), {
    id: "draft",
    now: NOW,
  });
  const mainFeed = updateFeedItems(createEmptyFeed(NOW), [draft, published], { now: NOW });
  const github = createGitHubFake({ branches: ["main"], files: { main: mainFeed } });

  const response = await handlePublicUpdates(
    new Request(`${ORIGIN}/api/updates`),
    { env: ENV, fetchImpl: github.fetchImpl, now: NOW },
  );
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("X-Updates-Source"), "main");
  const publicFeed = await response.json();
  assert.equal(publicFeed.revision, mainFeed.revision);
  assert.deepEqual(publicFeed.items.map((item) => item.id), ["published"]);
  assert.equal(github.state.requests.some((request) => request.method === "PUT"), false);
});

test("content 파일이 잘못된 UTF-8이면 main fallback을 사용한다", async () => {
  const mainFeed = updateFeedItems(
    createEmptyFeed(NOW),
    [createUpdateItem(updateInput(), { id: "main-valid", now: NOW })],
    { now: NOW },
  );
  const github = createGitHubFake({ files: { main: mainFeed } });
  const originalFetch = github.fetchImpl;
  const fetchImpl = async (url, init) => {
    const parsed = new URL(url);
    if (
      parsed.pathname.endsWith("/contents/site_updates.json") &&
      parsed.searchParams.get("ref") === "content"
    ) {
      return jsonResponse({
        type: "file",
        encoding: "base64",
        content: Buffer.from([0x7b, 0x22, 0xff, 0x22, 0x3a, 0x31, 0x7d]).toString("base64"),
        sha: "invalid-utf8",
      });
    }
    return originalFetch(url, init);
  };

  const response = await handlePublicUpdates(
    new Request(`${ORIGIN}/api/updates`),
    { env: ENV, fetchImpl, now: NOW },
  );
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("X-Updates-Source"), "main");
  assert.deepEqual((await response.json()).items.map((item) => item.id), ["main-valid"]);
});

test("GitHub 네트워크 오류는 공개 API의 명확한 503으로 정규화한다", async () => {
  const response = await handlePublicUpdates(
    new Request(`${ORIGIN}/api/updates`),
    {
      env: ENV,
      fetchImpl: async () => {
        throw new TypeError("network unavailable");
      },
      now: NOW,
    },
  );

  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, "UPDATES_UNAVAILABLE");
});

test("변경 요청은 동일 Origin을 요구하고 GitHub 호출 전에 거부한다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(
    adminRequest("POST", updateInput(), { origin: "https://attacker.example" }),
    { env: ENV, fetchImpl: github.fetchImpl, now: () => NOW },
  );
  assert.equal(response.status, 403);
  assert.equal(github.state.requests.length, 0);
});

test("세션이 없는 관리자 요청은 GitHub 호출 전에 401로 거부한다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(
    new Request(`${ORIGIN}/api/admin/updates`),
    { env: ENV, fetchImpl: github.fetchImpl, now: () => NOW },
  );
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error.code, "AUTH_REQUIRED");
  assert.equal(github.state.requests.length, 0);
});

test("관리자 payload의 릴리스·EXE 필드는 422로 거부하고 쓰지 않는다", async () => {
  const github = createGitHubFake({ files: { content: createEmptyFeed(NOW) } });
  const response = await handleAdminUpdates(
    adminRequest("POST", {
      ...updateInput(),
      latest_version: "99.99.99",
      download: { url: "https://attacker.example/app.exe" },
    }),
    { env: ENV, fetchImpl: github.fetchImpl, now: () => NOW },
  );
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, "INVALID_UPDATE");
  assert.equal(github.state.requests.some((request) => request.method === "PUT"), false);
});
