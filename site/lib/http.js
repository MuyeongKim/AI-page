const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
};

export class HttpError extends Error {
  constructor(status, code, message, details = undefined) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function jsonResponse(data, { status = 200, headers = {} } = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...JSON_HEADERS,
      "Cache-Control": "no-store",
      ...headers,
    },
  });
}

export function errorResponse(error) {
  if (error instanceof HttpError) {
    const body = {
      error: {
        code: error.code,
        message: error.message,
      },
    };
    if (error.details !== undefined) {
      body.error.details = error.details;
    }
    return jsonResponse(body, { status: error.status });
  }

  console.error("관리자 API 처리 중 예기치 않은 오류", error);
  return jsonResponse(
    {
      error: {
        code: "INTERNAL_ERROR",
        message: "요청을 처리하지 못했습니다.",
      },
    },
    { status: 500 },
  );
}

export function methodNotAllowed(allowedMethods) {
  return jsonResponse(
    {
      error: {
        code: "METHOD_NOT_ALLOWED",
        message: "허용되지 않은 요청 방식입니다.",
      },
    },
    {
      status: 405,
      headers: { Allow: allowedMethods.join(", ") },
    },
  );
}

export function requireSameOrigin(request) {
  const origin = request.headers.get("Origin");
  if (!origin) {
    throw new HttpError(403, "ORIGIN_REQUIRED", "Origin 헤더가 필요합니다.");
  }

  let expectedOrigin;
  try {
    expectedOrigin = new URL(request.url).origin;
  } catch {
    throw new HttpError(400, "INVALID_REQUEST_URL", "요청 URL이 올바르지 않습니다.");
  }

  if (origin !== expectedOrigin) {
    throw new HttpError(403, "ORIGIN_MISMATCH", "동일 출처 요청만 허용됩니다.");
  }
}

export async function readJson(request, { maxBytes = 16_384 } = {}) {
  const contentType = request.headers.get("Content-Type") ?? "";
  if (!contentType.toLowerCase().startsWith("application/json")) {
    throw new HttpError(415, "JSON_REQUIRED", "application/json 요청만 허용됩니다.");
  }

  const declaredLength = Number(request.headers.get("Content-Length"));
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    throw new HttpError(413, "BODY_TOO_LARGE", "요청 본문이 너무 큽니다.");
  }

  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > maxBytes) {
    throw new HttpError(413, "BODY_TOO_LARGE", "요청 본문이 너무 큽니다.");
  }
  if (!text.trim()) {
    throw new HttpError(400, "EMPTY_BODY", "JSON 요청 본문이 필요합니다.");
  }

  try {
    const value = JSON.parse(text);
    if (value === null || Array.isArray(value) || typeof value !== "object") {
      throw new HttpError(400, "OBJECT_REQUIRED", "JSON 객체를 전달해야 합니다.");
    }
    return value;
  } catch (error) {
    if (error instanceof HttpError) {
      throw error;
    }
    throw new HttpError(400, "INVALID_JSON", "JSON 형식이 올바르지 않습니다.");
  }
}
