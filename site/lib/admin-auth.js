import {
  createHmac,
  randomBytes,
  scrypt as nodeScrypt,
  timingSafeEqual,
} from "node:crypto";
import { promisify } from "node:util";

import { HttpError } from "./http.js";


export const ADMIN_COOKIE_NAME = "site_admin_session";
export const ADMIN_COOKIE_PATH = "/api/admin";
export const ADMIN_SESSION_TTL_SECONDS = 2 * 60 * 60;

const SCRYPT_N = 16_384;
const SCRYPT_R = 8;
const SCRYPT_P = 5;
const SCRYPT_KEY_LENGTH = 64;
const SCRYPT_MAX_MEMORY = 64 * 1024 * 1024;
const scrypt = promisify(nodeScrypt);

function byteLength(value) {
  return new TextEncoder().encode(value).byteLength;
}

function requireSessionSecret(env) {
  const secret = env.ADMIN_SESSION_SECRET;
  if (typeof secret !== "string" || byteLength(secret) < 32) {
    throw new HttpError(
      503,
      "AUTH_NOT_CONFIGURED",
      "ADMIN_SESSION_SECRET은 32바이트 이상의 값으로 설정해야 합니다.",
    );
  }
  return secret;
}

function parsePasswordHash(encoded) {
  if (typeof encoded !== "string") {
    throw new Error("해시가 문자열이 아닙니다.");
  }

  const [algorithm, nText, rText, pText, saltText, digestText, extra] = encoded.split("$");
  const N = Number(nText);
  const r = Number(rText);
  const p = Number(pText);
  if (
    algorithm !== "scrypt" ||
    extra !== undefined ||
    N !== SCRYPT_N ||
    r !== SCRYPT_R ||
    p !== SCRYPT_P
  ) {
    throw new Error("scrypt 파라미터가 올바르지 않습니다.");
  }

  const salt = Buffer.from(saltText ?? "", "base64url");
  const digest = Buffer.from(digestText ?? "", "base64url");
  if (salt.length < 16 || salt.length > 64 || digest.length < 32 || digest.length > 128) {
    throw new Error("scrypt salt 또는 digest 길이가 올바르지 않습니다.");
  }
  return { N, r, p, salt, digest };
}

function validatePassword(password) {
  if (typeof password !== "string" || password.length === 0 || byteLength(password) > 1_024) {
    throw new HttpError(400, "INVALID_PASSWORD", "비밀번호 형식이 올바르지 않습니다.");
  }
}

async function derivePassword(password, { N, r, p, salt, keyLength }) {
  return scrypt(password, salt, keyLength, {
    N,
    r,
    p,
    maxmem: SCRYPT_MAX_MEMORY,
  });
}

export async function hashAdminPassword(password, { salt = randomBytes(16) } = {}) {
  validatePassword(password);
  if (!Buffer.isBuffer(salt) || salt.length < 16 || salt.length > 64) {
    throw new Error("salt는 16~64바이트 Buffer여야 합니다.");
  }

  const digest = await derivePassword(password, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
    salt,
    keyLength: SCRYPT_KEY_LENGTH,
  });
  return [
    "scrypt",
    SCRYPT_N,
    SCRYPT_R,
    SCRYPT_P,
    salt.toString("base64url"),
    Buffer.from(digest).toString("base64url"),
  ].join("$");
}

export async function verifyAdminPassword(password, env) {
  validatePassword(password);
  let parsed;
  try {
    parsed = parsePasswordHash(env.ADMIN_PASSWORD_HASH);
  } catch {
    throw new HttpError(
      503,
      "AUTH_NOT_CONFIGURED",
      "ADMIN_PASSWORD_HASH 설정이 올바르지 않습니다.",
    );
  }

  const actual = Buffer.from(
    await derivePassword(password, {
      ...parsed,
      keyLength: parsed.digest.length,
    }),
  );
  return actual.length === parsed.digest.length && timingSafeEqual(actual, parsed.digest);
}

function signPayload(encodedPayload, secret) {
  return createHmac("sha256", secret).update(encodedPayload).digest("base64url");
}

function parseCookies(header) {
  const cookies = new Map();
  for (const part of (header ?? "").split(";")) {
    const separator = part.indexOf("=");
    if (separator <= 0) {
      continue;
    }
    cookies.set(part.slice(0, separator).trim(), part.slice(separator + 1).trim());
  }
  return cookies;
}

export function createAdminSession(env, { now = new Date(), nonce = randomBytes(18) } = {}) {
  const secret = requireSessionSecret(env);
  const issuedAt = Math.floor(new Date(now).getTime() / 1000);
  if (!Number.isSafeInteger(issuedAt)) {
    throw new HttpError(500, "INVALID_CLOCK", "서버 시각을 확인할 수 없습니다.");
  }

  const expiresAt = issuedAt + ADMIN_SESSION_TTL_SECONDS;
  const payload = {
    v: 1,
    iat: issuedAt,
    exp: expiresAt,
    nonce: Buffer.from(nonce).toString("base64url"),
  };
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const token = `${encodedPayload}.${signPayload(encodedPayload, secret)}`;
  const cookie = [
    `${ADMIN_COOKIE_NAME}=${token}`,
    `Path=${ADMIN_COOKIE_PATH}`,
    "HttpOnly",
    "Secure",
    "SameSite=Strict",
    `Max-Age=${ADMIN_SESSION_TTL_SECONDS}`,
    "Priority=High",
  ].join("; ");

  return {
    token,
    cookie,
    expires_at: new Date(expiresAt * 1000).toISOString(),
  };
}

export function clearAdminSessionCookie() {
  return [
    `${ADMIN_COOKIE_NAME}=`,
    `Path=${ADMIN_COOKIE_PATH}`,
    "HttpOnly",
    "Secure",
    "SameSite=Strict",
    "Max-Age=0",
    "Expires=Thu, 01 Jan 1970 00:00:00 GMT",
    "Priority=High",
  ].join("; ");
}

export function verifyAdminSession(request, env, { now = new Date() } = {}) {
  const token = parseCookies(request.headers.get("Cookie")).get(ADMIN_COOKIE_NAME);
  if (!token) {
    throw new HttpError(401, "AUTH_REQUIRED", "관리자 로그인이 필요합니다.");
  }

  const separator = token.indexOf(".");
  if (separator <= 0 || separator !== token.lastIndexOf(".")) {
    throw new HttpError(401, "INVALID_SESSION", "관리자 세션이 올바르지 않습니다.");
  }

  const encodedPayload = token.slice(0, separator);
  const suppliedSignature = Buffer.from(token.slice(separator + 1), "base64url");
  const expectedSignature = Buffer.from(
    signPayload(encodedPayload, requireSessionSecret(env)),
    "base64url",
  );
  if (
    suppliedSignature.length !== expectedSignature.length ||
    !timingSafeEqual(suppliedSignature, expectedSignature)
  ) {
    throw new HttpError(401, "INVALID_SESSION", "관리자 세션이 올바르지 않습니다.");
  }

  let payload;
  try {
    payload = JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8"));
  } catch {
    throw new HttpError(401, "INVALID_SESSION", "관리자 세션이 올바르지 않습니다.");
  }

  const nowSeconds = Math.floor(new Date(now).getTime() / 1000);
  if (
    payload?.v !== 1 ||
    !Number.isSafeInteger(payload.iat) ||
    !Number.isSafeInteger(payload.exp) ||
    typeof payload.nonce !== "string" ||
    payload.nonce.length < 16 ||
    payload.iat > nowSeconds + 60 ||
    payload.exp <= nowSeconds ||
    payload.exp - payload.iat !== ADMIN_SESSION_TTL_SECONDS
  ) {
    throw new HttpError(401, "EXPIRED_SESSION", "관리자 세션이 만료되었거나 올바르지 않습니다.");
  }
  return payload;
}
