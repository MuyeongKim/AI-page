import {
  clearAdminSessionCookie,
  verifyAdminSession,
} from "../../lib/admin-auth.js";
import { HttpError, errorResponse, jsonResponse, methodNotAllowed } from "../../lib/http.js";


export async function handleAdminSession(
  request,
  { env = process.env, now = new Date() } = {},
) {
  if (request.method !== "GET") {
    return methodNotAllowed(["GET"]);
  }

  try {
    const session = verifyAdminSession(request, env, { now });
    return jsonResponse({
      authenticated: true,
      expires_at: new Date(session.exp * 1000).toISOString(),
    });
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      return jsonResponse(
        { authenticated: false },
        { headers: { "Set-Cookie": clearAdminSessionCookie() } },
      );
    }
    return errorResponse(error);
  }
}

export default {
  fetch: handleAdminSession,
};
