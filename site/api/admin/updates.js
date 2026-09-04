import { randomUUID } from "node:crypto";

import { verifyAdminSession } from "../../lib/admin-auth.js";
import { readAdminUpdates, writeAdminUpdates } from "../../lib/github-updates.js";
import {
  HttpError,
  errorResponse,
  jsonResponse,
  methodNotAllowed,
  readJson,
  requireSameOrigin,
} from "../../lib/http.js";
import {
  UpdateSchemaError,
  createUpdateItem,
  patchUpdateItem,
  updateFeedItems,
} from "../../lib/updates-schema.js";


function asSchemaHttpError(error) {
  if (error instanceof UpdateSchemaError) {
    return new HttpError(422, "INVALID_UPDATE", error.message, error.details);
  }
  return error;
}

function currentTime(now) {
  return typeof now === "function" ? now() : now;
}

function requireExactKeys(body, keys, message) {
  const actual = Object.keys(body).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new HttpError(400, "INVALID_CRUD_BODY", message);
  }
}

function requireCurrentRevision(body, feed) {
  if (!Number.isSafeInteger(body.expected_revision) || body.expected_revision < 0) {
    throw new HttpError(
      400,
      "INVALID_REVISION",
      "확인한 공지의 변경 이력을 알 수 없습니다. 목록을 새로고침해 주세요.",
    );
  }
  if (body.expected_revision !== feed.revision) {
    throw new HttpError(
      409,
      "UPDATE_REVISION_CONFLICT",
      "다른 변경이 먼저 저장되었습니다. 최신 저장본과 비교한 뒤 다시 시도해 주세요.",
    );
  }
}

export async function handleAdminUpdates(
  request,
  {
    env = process.env,
    fetchImpl = fetch,
    now = () => new Date(),
    createId = randomUUID,
  } = {},
) {
  const allowedMethods = ["GET", "POST", "PATCH", "DELETE"];
  if (!allowedMethods.includes(request.method)) {
    return methodNotAllowed(allowedMethods);
  }

  try {
    if (request.method !== "GET") {
      requireSameOrigin(request);
    }
    verifyAdminSession(request, env, { now: currentTime(now) });
    const stored = await readAdminUpdates({ env, fetchImpl, now: currentTime(now) });

    if (request.method === "GET") {
      return jsonResponse(stored.feed);
    }

    const body = await readJson(request, { maxBytes: 64 * 1024 });
    let item;
    let items;
    let responseBody;
    let message;
    const operationTime = currentTime(now);

    if (request.method === "POST") {
      item = createUpdateItem(body, { id: createId(), now: operationTime });
      items = [item, ...stored.feed.items];
      message = `관리자 공지 추가: ${item.id}`;
    } else if (request.method === "PATCH") {
      requireExactKeys(
        body,
        ["id", "changes", "expected_revision"],
        "수정 요청 형식이 올바르지 않습니다. 작성 내용을 복사해 둔 뒤 페이지를 새로고침해 주세요.",
      );
      requireCurrentRevision(body, stored.feed);
      const index = stored.feed.items.findIndex((candidate) => candidate.id === body.id);
      if (index < 0) {
        throw new HttpError(404, "UPDATE_NOT_FOUND", "수정할 공지를 찾을 수 없습니다.");
      }
      item = patchUpdateItem(stored.feed.items[index], body.changes, { now: operationTime });
      items = stored.feed.items.with(index, item);
      message = `관리자 공지 수정: ${item.id}`;
    } else {
      requireExactKeys(
        body,
        ["id", "expected_revision"],
        "삭제 요청 형식이 올바르지 않습니다. 페이지를 새로고침해 주세요.",
      );
      requireCurrentRevision(body, stored.feed);
      if (typeof body.id !== "string") {
        throw new HttpError(400, "INVALID_UPDATE_ID", "id가 올바르지 않습니다.");
      }
      items = stored.feed.items.filter((candidate) => candidate.id !== body.id);
      if (items.length === stored.feed.items.length) {
        throw new HttpError(404, "UPDATE_NOT_FOUND", "삭제할 공지를 찾을 수 없습니다.");
      }
      message = `관리자 공지 삭제: ${body.id}`;
    }

    const feed = updateFeedItems(stored.feed, items, { now: operationTime });
    await writeAdminUpdates({
      config: stored.config,
      feed,
      sha: stored.sha,
      message,
      fetchImpl,
    });

    if (request.method === "DELETE") {
      responseBody = { deleted_id: body.id, feed };
    } else {
      responseBody = { item, feed };
    }
    return jsonResponse(responseBody, { status: request.method === "POST" ? 201 : 200 });
  } catch (error) {
    return errorResponse(asSchemaHttpError(error));
  }
}

export default {
  fetch: handleAdminUpdates,
};
