import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const scriptPath = resolve(siteRoot, "../scripts/export_release.py");
const candidates = [process.env.PYTHON, "python3", "python"].filter(Boolean);

for (const command of candidates) {
  const result = spawnSync(command, [scriptPath, "--check"], {
    cwd: resolve(siteRoot, ".."),
    encoding: "utf8",
  });

  if (result.error?.code === "ENOENT") {
    continue;
  }

  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  process.exit(result.status ?? 1);
}

console.error("릴리스 피드를 검사할 Python 실행 파일을 찾지 못했습니다.");
process.exit(1);
