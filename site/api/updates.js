import { errorResponse, jsonResponse, methodNotAllowed } from "../lib/http.js";
import { readPublicUpdates } from "../lib/github-updates.js";
import { toPublicFeed } from "../lib/updates-schema.js";


export async function handlePublicUpdates(
  request,
  { env = process.env, fetchImpl = fetch, now = new Date() } = {},
) {
  if (request.method !== "GET") {
    return methodNotAllowed(["GET"]);
  }

  try {
    const { feed, source } = await readPublicUpdates({ env, fetchImpl });
    return jsonResponse(toPublicFeed(feed, { now }), {
      headers: {
        "Cache-Control": "public, max-age=0, s-maxage=60, stale-while-revalidate=300",
        "X-Updates-Source": source,
      },
    });
  } catch (error) {
    return errorResponse(error);
  }
}

export default {
  fetch: handlePublicUpdates,
};
