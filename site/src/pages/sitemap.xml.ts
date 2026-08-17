import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const entry = site
    ? `<url><loc>${new URL("/", site)}</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>`
    : "";
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entry}</urlset>\n`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
