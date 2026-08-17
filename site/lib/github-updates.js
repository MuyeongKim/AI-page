import { HttpError } from "./http.js";
import {
  UpdateSchemaError,
  createEmptyFeed,
  validateUpdatesFeed,
} from "./updates-schema.js";


export const UPDATES_PATH = "site_updates.json";
export const MAIN_FALLBACK_BRANCH = "main";

const GITHUB_API = "https://api.github.com";
const GITHUB_API_VERSION = "2022-11-28";
const GITHUB_REQUEST_TIMEOUT_MS = 5_000;
const MAX_FEED_BYTES = 256 * 1024;
const REPOSITORY_PART_PATTERN = /^[A-Za-z0-9_.-]+$/;

function configurationError(message) {
  return new HttpError(503, "GITHUB_NOT_CONFIGURED", message);
}

export function getGitHubConfig(env, { requireToken = false } = {}) {
  const owner = env.GITHUB_CONTENT_OWNER || "MuyeongKim";
  const repo = env.GITHUB_CONTENT_REPO || "AI-page";
  const branch = env.GITHUB_CONTENT_BRANCH || "content";
  const token = env.GITHUB_CONTENT_TOKEN || null;

  if (!REPOSITORY_PART_PATTERN.test(owner) || !REPOSITORY_PART_PATTERN.test(repo)) {
    throw configurationError("GitHub 저장소 소유자 또는 이름 설정이 올바르지 않습니다.");
  }
  if (
    typeof branch !== "string" ||
    !branch.trim() ||
    branch.length > 255 ||
    /[\u0000-\u001F\u007F]/.test(branch)
  ) {
    throw configurationError("GITHUB_CONTENT_BRANCH 설정이 올바르지 않습니다.");
  }
  if (branch === MAIN_FALLBACK_BRANCH) {
    throw configurationError("공지 쓰기 브랜치는 main과 분리해야 합니다.");
  }
  if (requireToken && (!token || typeof token !== "string")) {
    throw configurationError("GITHUB_CONTENT_TOKEN이 설정되지 않았습니다.");
  }

  return { owner, repo, branch, token };
}

function githubHeaders(config) {
  const headers = {
    Accept: "application/vnd.github+json",
    "User-Agent": "stayup-ai-site-updates",
    "X-GitHub-Api-Version": GITHUB_API_VERSION,
  };
  if (config.token) {
    headers.Authorization = `Bearer ${config.token}`;
  }
  return headers;
}

function repositoryUrl(config, suffix) {
  return `${GITHUB_API}/repos/${encodeURIComponent(config.owner)}/${encodeURIComponent(config.repo)}${suffix}`;
}

async function requestGitHub(fetchImpl, url, init = {}) {
  try {
    return await fetchImpl(url, {
      ...init,
      signal: AbortSignal.timeout(GITHUB_REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new HttpError(503, "GITHUB_UNAVAILABLE", "GitHub API에 연결하지 못했습니다.");
  }
}

async function responseJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function ensureContentBranch(config, fetchImpl) {
  const response = await requestGitHub(
    fetchImpl,
    repositoryUrl(config, `/branches/${encodeURIComponent(config.branch)}`),
    { headers: githubHeaders(config) },
  );
  if (response.status === 404) {
    throw new HttpError(
      503,
      "CONTENT_BRANCH_MISSING",
      `GitHub content 브랜치(${config.branch})가 없습니다. 먼저 브랜치를 생성해야 합니다.`,
    );
  }
  if (!response.ok) {
    throw new HttpError(503, "GITHUB_UNAVAILABLE", "GitHub content 브랜치를 확인하지 못했습니다.");
  }
}

function decodeFeed(payload, source) {
  if (
    payload === null ||
    payload.type !== "file" ||
    payload.encoding !== "base64" ||
    typeof payload.content !== "string" ||
    typeof payload.sha !== "string"
  ) {
    throw new HttpError(502, "INVALID_GITHUB_CONTENT", `${source} 공지 파일 응답이 올바르지 않습니다.`);
  }

  const bytes = Buffer.from(payload.content.replace(/\s/g, ""), "base64");
  if (bytes.length === 0 || bytes.length > MAX_FEED_BYTES) {
    throw new HttpError(502, "INVALID_UPDATES_FEED", `${source} 공지 파일 크기가 올바르지 않습니다.`);
  }

  let parsed;
  try {
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    parsed = JSON.parse(decoded);
  } catch {
    throw new HttpError(502, "INVALID_UPDATES_FEED", `${source} 공지 JSON이 올바르지 않습니다.`);
  }

  try {
    return { feed: validateUpdatesFeed(parsed), sha: payload.sha };
  } catch (error) {
    if (error instanceof UpdateSchemaError) {
      throw new HttpError(502, "INVALID_UPDATES_FEED", `${source} 공지 계약이 올바르지 않습니다.`);
    }
    throw error;
  }
}

async function readFile(config, branch, fetchImpl) {
  const response = await requestGitHub(
    fetchImpl,
    repositoryUrl(
      config,
      `/contents/${UPDATES_PATH}?ref=${encodeURIComponent(branch)}`,
    ),
    { headers: githubHeaders(config) },
  );
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new HttpError(503, "GITHUB_UNAVAILABLE", "GitHub 공지 파일을 읽지 못했습니다.");
  }
  return decodeFeed(await responseJson(response), `${branch}/${UPDATES_PATH}`);
}

export async function readAdminUpdates({ env, fetchImpl = fetch, now = new Date() }) {
  const config = getGitHubConfig(env, { requireToken: true });
  await ensureContentBranch(config, fetchImpl);
  const stored = await readFile(config, config.branch, fetchImpl);
  const fallback = stored === null ? await readFile(config, MAIN_FALLBACK_BRANCH, fetchImpl) : null;
  return {
    config,
    feed: stored?.feed ?? fallback?.feed ?? createEmptyFeed(now),
    sha: stored?.sha ?? null,
  };
}

export async function readPublicUpdates({ env, fetchImpl = fetch }) {
  const config = getGitHubConfig(env);
  try {
    const content = await readFile(config, config.branch, fetchImpl);
    if (content !== null) {
      return { ...content, source: config.branch };
    }
  } catch (error) {
    if (!(error instanceof HttpError)) {
      throw error;
    }
  }

  try {
    const fallback = await readFile(config, MAIN_FALLBACK_BRANCH, fetchImpl);
    if (fallback !== null) {
      return { ...fallback, source: MAIN_FALLBACK_BRANCH };
    }
  } catch (error) {
    if (!(error instanceof HttpError)) {
      throw error;
    }
  }

  throw new HttpError(
    503,
    "UPDATES_UNAVAILABLE",
    "공개 공지 피드를 현재 사용할 수 없습니다.",
  );
}

export async function writeAdminUpdates({
  config,
  feed,
  sha,
  message,
  fetchImpl = fetch,
}) {
  const validated = validateUpdatesFeed(feed);
  const serialized = Buffer.from(`${JSON.stringify(validated, null, 2)}\n`, "utf8");
  if (serialized.length > MAX_FEED_BYTES) {
    throw new HttpError(422, "FEED_TOO_LARGE", "공지 피드는 256KiB를 초과할 수 없습니다.");
  }
  const content = serialized.toString("base64");
  const body = {
    message,
    content,
    branch: config.branch,
  };
  if (sha !== null) {
    body.sha = sha;
  }

  const response = await requestGitHub(
    fetchImpl,
    repositoryUrl(config, `/contents/${UPDATES_PATH}`),
    {
      method: "PUT",
      headers: {
        ...githubHeaders(config),
        "Content-Type": "application/json; charset=utf-8",
      },
      body: JSON.stringify(body),
    },
  );

  if (response.status === 409) {
    throw new HttpError(
      409,
      "BLOB_SHA_CONFLICT",
      "다른 변경이 먼저 저장되었습니다. 목록을 새로고침한 뒤 다시 시도하세요.",
    );
  }
  if (response.status === 422) {
    const payload = await responseJson(response);
    const diagnostic = JSON.stringify(payload ?? {});
    if (/sha|already exists/i.test(diagnostic)) {
      throw new HttpError(
        409,
        "BLOB_SHA_CONFLICT",
        "다른 변경이 먼저 저장되었습니다. 목록을 새로고침한 뒤 다시 시도하세요.",
      );
    }
    throw new HttpError(503, "GITHUB_WRITE_FAILED", "GitHub 공지 파일을 저장하지 못했습니다.");
  }
  if (response.status === 404) {
    throw new HttpError(
      503,
      "CONTENT_BRANCH_MISSING",
      `GitHub content 브랜치(${config.branch}) 또는 저장 경로를 찾을 수 없습니다.`,
    );
  }
  if (!response.ok) {
    throw new HttpError(503, "GITHUB_WRITE_FAILED", "GitHub 공지 파일을 저장하지 못했습니다.");
  }

  const payload = await responseJson(response);
  return {
    sha: typeof payload?.content?.sha === "string" ? payload.content.sha : null,
  };
}
