import { createAdminSession, verifyAdminPassword } from "../../lib/admin-auth.js";
import {
  HttpError,
  errorResponse,
  jsonResponse,
  methodNotAllowed,
  readJson,
  requireSameOrigin,
} from "../../lib/http.js";


export async function handleAdminLogin(
  request,
  { env = process.env, now = new Date() } = {},
) {
  if (request.method !== "POST") {
    return methodNotAllowed(["POST"]);
  }

  try {
    requireSameOrigin(request);
    const body = await readJson(request, { maxBytes: 4_096 });
    if (Object.keys(body).some((key) => key !== "password")) {
      throw new HttpError(400, "INVALID_LOGIN_BODY", "password 필드만 전달할 수 있습니다.");
    }
    if (!(await verifyAdminPassword(body.password, env))) {
      throw new HttpError(401, "INVALID_CREDENTIALS", "관리자 인증 정보가 올바르지 않습니다.");
    }

    const session = createAdminSession(env, { now });
    return jsonResponse(
      { ok: true, expires_at: session.expires_at },
      { headers: { "Set-Cookie": session.cookie } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}

export default {
  fetch: handleAdminLogin,
};
