import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

import {
  ADMIN_SESSION_TTL_SECONDS,
  createAdminSession,
  hashAdminPassword,
  verifyAdminPassword,
  verifyAdminSession,
} from "../lib/admin-auth.js";
import loginFunction, { handleAdminLogin } from "../api/admin/login.js";
import logoutFunction, { handleAdminLogout } from "../api/admin/logout.js";
import sessionFunction, { handleAdminSession } from "../api/admin/session.js";


const PASSWORD = "correct horse battery staple";
const NOW = new Date("2026-08-17T12:00:00.000Z");
const ENV = {
  ADMIN_PASSWORD_HASH: await hashAdminPassword(PASSWORD, { salt: Buffer.alloc(16, 7) }),
  ADMIN_SESSION_SECRET: "test-session-secret-that-is-at-least-32-bytes",
};

test("Vercel 인증 함수도 Web Standard fetch 엔트리포인트를 제공한다", async () => {
  const functions = [loginFunction, logoutFunction, sessionFunction];
  assert.equal(functions.every((entrypoint) => typeof entrypoint.fetch === "function"), true);

  const responses = await Promise.all([
    loginFunction.fetch(new Request("https://updates.example/api/admin/login")),
    logoutFunction.fetch(new Request("https://updates.example/api/admin/logout")),
    sessionFunction.fetch(
      new Request("https://updates.example/api/admin/session", { method: "POST" }),
    ),
  ]);
  assert.deepEqual(
    responses.map((response) => response.status),
    [405, 405, 405],
  );
  assert.equal(responses.every((response) => response instanceof Response), true);
});

test("scrypt 해시는 비밀번호 원문을 저장하지 않고 상수시간 검증에 사용된다", async () => {
  assert.match(ENV.ADMIN_PASSWORD_HASH, /^scrypt\$16384\$8\$5\$/);
  assert.equal(ENV.ADMIN_PASSWORD_HASH.includes(PASSWORD), false);
  assert.equal(await verifyAdminPassword(PASSWORD, ENV), true);
  assert.equal(await verifyAdminPassword("wrong password", ENV), false);
});

test("관리자 세션은 HMAC 서명과 엄격한 보안 쿠키 속성을 사용한다", () => {
  assert.equal(ADMIN_SESSION_TTL_SECONDS, 2 * 60 * 60);
  const session = createAdminSession(ENV, { now: NOW, nonce: Buffer.alloc(18, 3) });
  assert.match(session.cookie, /HttpOnly/);
  assert.match(session.cookie, /Secure/);
  assert.match(session.cookie, /SameSite=Strict/);
  assert.match(session.cookie, /Path=\/api\/admin/);
  assert.match(session.cookie, new RegExp(`Max-Age=${ADMIN_SESSION_TTL_SECONDS}`));

  const request = new Request("https://updates.example/api/admin/session", {
    headers: { Cookie: session.cookie.split(";", 1)[0] },
  });
  const payload = verifyAdminSession(request, ENV, { now: NOW });
  assert.equal(payload.v, 1);
  assert.equal(payload.exp - payload.iat, ADMIN_SESSION_TTL_SECONDS);
});

test("위변조되거나 만료된 세션은 거부한다", () => {
  const session = createAdminSession(ENV, { now: NOW, nonce: Buffer.alloc(18, 5) });
  const [name, token] = session.cookie.split(";", 1)[0].split("=");
  const tampered = new Request("https://updates.example/api/admin/session", {
    headers: { Cookie: `${name}=${token.slice(0, -1)}x` },
  });
  assert.throws(
    () => verifyAdminSession(tampered, ENV, { now: NOW }),
    (error) => error.status === 401,
  );

  const expired = new Request("https://updates.example/api/admin/session", {
    headers: { Cookie: `${name}=${token}` },
  });
  assert.throws(
    () =>
      verifyAdminSession(expired, ENV, {
        now: new Date(NOW.getTime() + (ADMIN_SESSION_TTL_SECONDS + 1) * 1000),
      }),
    (error) => error.status === 401,
  );
});

test("로그인은 동일 Origin만 허용하고 비밀번호나 해시를 응답하지 않는다", async () => {
  const crossOrigin = await handleAdminLogin(
    new Request("https://updates.example/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: "https://attacker.example" },
      body: JSON.stringify({ password: PASSWORD }),
    }),
    { env: ENV, now: NOW },
  );
  assert.equal(crossOrigin.status, 403);

  const response = await handleAdminLogin(
    new Request("https://updates.example/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: "https://updates.example" },
      body: JSON.stringify({ password: PASSWORD }),
    }),
    { env: ENV, now: NOW },
  );
  assert.equal(response.status, 200);
  assert.match(response.headers.get("Set-Cookie"), /HttpOnly/);
  const responseText = await response.text();
  assert.equal(responseText.includes(PASSWORD), false);
  assert.equal(responseText.includes(ENV.ADMIN_PASSWORD_HASH), false);
});

test("세션 확인과 로그아웃은 쿠키를 브라우저에 노출하지 않고 만료 처리한다", async () => {
  const session = createAdminSession(ENV, { now: NOW, nonce: Buffer.alloc(18, 4) });
  const cookie = session.cookie.split(";", 1)[0];
  const sessionResponse = await handleAdminSession(
    new Request("https://updates.example/api/admin/session", { headers: { Cookie: cookie } }),
    { env: ENV, now: NOW },
  );
  assert.equal(sessionResponse.status, 200);
  assert.equal((await sessionResponse.json()).authenticated, true);

  const logoutResponse = await handleAdminLogout(
    new Request("https://updates.example/api/admin/logout", {
      method: "POST",
      headers: { Origin: "https://updates.example", Cookie: cookie },
    }),
  );
  assert.equal(logoutResponse.status, 200);
  assert.match(logoutResponse.headers.get("Set-Cookie"), /Max-Age=0/);
  assert.match(logoutResponse.headers.get("Set-Cookie"), /HttpOnly/);
  assert.equal((await logoutResponse.json()).ok, true);
});

test("해시 생성 스크립트는 stdin 비밀번호로 환경변수 형식만 출력한다", () => {
  const completed = spawnSync(
    process.execPath,
    [new URL("../scripts/hash-admin-password.mjs", import.meta.url).pathname, "--stdin"],
    { input: `${PASSWORD}\n`, encoding: "utf8" },
  );
  assert.equal(completed.status, 0, completed.stderr);
  assert.match(completed.stdout, /^ADMIN_PASSWORD_HASH=scrypt\$16384\$8\$5\$/);
  assert.equal(completed.stdout.includes(PASSWORD), false);
});
