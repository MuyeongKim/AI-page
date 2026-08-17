import { clearAdminSessionCookie } from "../../lib/admin-auth.js";
import {
  errorResponse,
  jsonResponse,
  methodNotAllowed,
  requireSameOrigin,
} from "../../lib/http.js";


export async function handleAdminLogout(request) {
  if (request.method !== "POST") {
    return methodNotAllowed(["POST"]);
  }

  try {
    requireSameOrigin(request);
    return jsonResponse(
      { ok: true },
      { headers: { "Set-Cookie": clearAdminSessionCookie() } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}

export default {
  fetch: handleAdminLogout,
};
