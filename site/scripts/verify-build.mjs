import { readdir, readFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { HtmlValidate } from "html-validate";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const projectRoot = resolve(siteRoot, "..");

const [
  html,
  adminHtml,
  releaseText,
  updateText,
  robots,
  sitemap,
  vercelText,
  socialImage,
  favicon,
] = await Promise.all([
  readFile(resolve(siteRoot, "dist/index.html"), "utf8"),
  readFile(resolve(siteRoot, "dist/admin/index.html"), "utf8"),
  readFile(resolve(projectRoot, "latest_version.json"), "utf8"),
  readFile(resolve(projectRoot, "site_updates.json"), "utf8"),
  readFile(resolve(siteRoot, "dist/robots.txt"), "utf8"),
  readFile(resolve(siteRoot, "dist/sitemap.xml"), "utf8"),
  readFile(resolve(siteRoot, "vercel.json"), "utf8"),
  stat(resolve(siteRoot, "dist/og.png")),
  stat(resolve(siteRoot, "dist/favicon.png")),
]);
const release = JSON.parse(releaseText);
const updateFeed = JSON.parse(updateText);
const vercel = JSON.parse(vercelText);
const fieldPhotoNames = [
  "app-interface.avif",
  "indoor-detection-demo.avif",
  "drone-demonstration.avif",
  "aerial-detection-results.avif",
];
const fieldPhotos = await Promise.all(
  fieldPhotoNames.map((name) => stat(resolve(siteRoot, "dist/images/field", name))),
);

const htmlValidate = new HtmlValidate();
const adminValidation = await htmlValidate.validateString(adminHtml);
if (!adminValidation.valid) {
  const messages = adminValidation.results
    .flatMap((result) => result.messages)
    .map((message) => `${message.ruleId}: ${message.message}`)
    .join(", ");
  throw new Error(`관리자 HTML 검증에 실패했습니다: ${messages}`);
}

const assetFiles = await readdir(resolve(siteRoot, "dist/_astro"));
const clientScriptNames = assetFiles.filter((name) => name.endsWith(".js"));
const clientScripts = await Promise.all(
  clientScriptNames.map((name) => readFile(resolve(siteRoot, "dist/_astro", name), "utf8")),
);
const clientJavaScript = clientScripts.join("\n");

const requiredText = [
  `V${release.version}`,
  release.release_date,
  "AI는 현장 판단을",
  "기존 현장 기록을",
  "실제 운용 성능을 보증하지 않습니다",
  "Windows 배포본",
  "AGPL-3.0",
];

for (const text of requiredText) {
  if (!html.includes(text)) {
    throw new Error(`빌드 결과에 필수 문구가 없습니다: ${text}`);
  }
}

for (const [index, photo] of fieldPhotos.entries()) {
  const name = fieldPhotoNames[index];
  if (photo.size === 0 || !html.includes(`/images/field/${name}`)) {
    throw new Error(`기존 현장 사진이 빌드 결과에 올바르게 포함되지 않았습니다: ${name}`);
  }
}

if (release.download?.status === "ready") {
  if (!release.download.url || !html.includes(release.download.url)) {
    throw new Error("준비된 Google Drive 다운로드 주소가 빌드 결과에 없습니다.");
  }
  for (const value of [release.download.filename, release.download.sha256]) {
    if (!value || !html.includes(value)) {
      throw new Error(`배포 파일 무결성 정보가 빌드 결과에 없습니다: ${value}`);
    }
  }
} else if (!html.includes("배포본 준비 중")) {
  throw new Error("배포 파일 준비 상태가 빌드 결과에 표시되지 않았습니다.");
}

for (const forbiddenText of ["인증키는", "V26.0409", "Made with Gamma"]) {
  if (html.includes(forbiddenText)) {
    throw new Error(`이전 공개 페이지의 금지 문구가 남아 있습니다: ${forbiddenText}`);
  }
}

const executableInlineScripts = (documentHtml) =>
  [...documentHtml.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].filter(
    ([, attributes, content]) =>
      !/\bsrc\s*=/.test(attributes) &&
      !/\btype\s*=\s*["']application\/(?:ld\+json|json)["']/i.test(attributes) &&
      content.trim().length > 0,
  );

for (const [route, routeHtml] of [
  ["/", html],
  ["/admin", adminHtml],
]) {
  if (executableInlineScripts(routeHtml).length > 0) {
    throw new Error(`${route} 빌드에 CSP가 차단할 인라인 실행 스크립트가 있습니다.`);
  }
}

const adminRequiredText = [
  "관리자 로그인",
  "초안 저장",
  "업데이트 목록",
  "실제 프로그램 버전은 변경되지 않습니다",
];
for (const text of adminRequiredText) {
  if (!adminHtml.includes(text)) {
    throw new Error(`관리자 빌드 결과에 필수 문구가 없습니다: ${text}`);
  }
}
if (!adminHtml.includes('name="robots" content="noindex, nofollow, noarchive"')) {
  throw new Error("관리자 페이지는 검색엔진 색인을 항상 차단해야 합니다.");
}
if (!html.includes(`data-revision="${updateFeed.revision}"`)) {
  throw new Error("랜딩페이지의 공지 fallback 리비전이 원본 JSON과 다릅니다.");
}

for (const endpoint of [
  "/api/updates",
  "/api/admin/session",
  "/api/admin/login",
  "/api/admin/logout",
  "/api/admin/updates",
]) {
  if (!clientJavaScript.includes(endpoint)) {
    throw new Error(`클라이언트 빌드에 필요한 API 호출이 없습니다: ${endpoint}`);
  }
}
for (const unsafeDomApi of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"] ) {
  if (clientJavaScript.includes(unsafeDomApi)) {
    throw new Error(`공지 클라이언트 코드에서 금지된 DOM API를 사용합니다: ${unsafeDomApi}`);
  }
}

const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]));
const pageAnchors = [
  ...html.matchAll(/\shref="#([^"]+)"/g),
].map((match) => match[1]);

for (const anchor of pageAnchors) {
  if (!ids.has(anchor)) {
    throw new Error(`페이지 내부 링크의 대상이 없습니다: #${anchor}`);
  }
}

const siteUrl = process.env.SITE_URL?.trim();
if (siteUrl) {
  const origin = new URL(siteUrl);
  if (origin.protocol !== "https:") {
    throw new Error("SITE_URL은 HTTPS 주소여야 합니다.");
  }
  if (!html.includes(`rel="canonical" href="${origin.origin}/"`)) {
    throw new Error("운영 주소의 canonical URL이 빌드 결과에 없습니다.");
  }
  if (!html.includes('name="robots" content="index, follow"')) {
    throw new Error("운영 주소 빌드는 검색엔진 색인을 허용해야 합니다.");
  }
  if (!robots.includes("Allow: /") || !sitemap.includes(origin.origin)) {
    throw new Error("운영 주소의 robots.txt 또는 sitemap.xml이 올바르지 않습니다.");
  }
} else {
  if (
    html.includes('rel="canonical"') ||
    !html.includes('name="robots" content="noindex, nofollow, noarchive"') ||
    !robots.includes("Disallow: /")
  ) {
    throw new Error("운영 주소 미설정 빌드는 검색엔진 색인을 차단해야 합니다.");
  }
}

if (vercel.buildCommand !== "npm test") {
  throw new Error("Vercel 빌드는 전체 랜딩페이지 검증을 실행해야 합니다.");
}
const responseHeaders = vercel.headers?.flatMap((rule) => rule.headers ?? []) ?? [];
const csp = responseHeaders.find((header) => header.key === "Content-Security-Policy")?.value;
if (!csp?.includes("frame-ancestors 'none'") || csp.includes("'unsafe-inline'")) {
  throw new Error("Vercel Content-Security-Policy가 기대한 보안 기준과 다릅니다.");
}

if (socialImage.size === 0 || favicon.size === 0) {
  throw new Error("소셜 미리보기 또는 favicon 파일이 비어 있습니다.");
}

console.log(`랜딩페이지 검증 완료: V${release.version}, 다운로드 ${release.download.status}`);
