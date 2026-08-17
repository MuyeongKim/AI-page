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
      requireExactKeys(body, ["id", "changes"], "PATCH에는 id와 changes가 필요합니다.");
      const index = stored.feed.items.findIndex((candidate) => candidate.id === body.id);
      if (index < 0) {
        throw new HttpError(404, "UPDATE_NOT_FOUND", "수정할 공지를 찾을 수 없습니다.");
      }
      item = patchUpdateItem(stored.feed.items[index], body.changes, { now: operationTime });
      items = stored.feed.items.with(index, item);
      message = `관리자 공지 수정: ${item.id}`;
    } else {
      requireExactKeys(body, ["id"], "DELETE에는 id가 필요합니다.");
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
