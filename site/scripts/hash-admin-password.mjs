#!/usr/bin/env node

import { stdin, stdout } from "node:process";

import { hashAdminPassword } from "../lib/admin-auth.js";


async function readAllStdin() {
  const chunks = [];
  for await (const chunk of stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8").replace(/[\r\n]+$/, "");
}

function readHidden(prompt) {
  if (!stdin.isTTY || typeof stdin.setRawMode !== "function") {
    return readAllStdin();
  }

  return new Promise((resolve, reject) => {
    const characters = [];
    stdout.write(prompt);
    stdin.setEncoding("utf8");
    stdin.setRawMode(true);
    stdin.resume();

    const finish = (error = null) => {
      stdin.off("data", onData);
      stdin.setRawMode(false);
      stdin.pause();
      stdout.write("\n");
      if (error) {
        reject(error);
      } else {
        resolve(characters.join(""));
      }
    };

    const onData = (chunk) => {
      for (const character of chunk) {
        if (character === "\u0003") {
          finish(new Error("사용자가 입력을 취소했습니다."));
          return;
        }
        if (character === "\r" || character === "\n") {
          finish();
          return;
        }
        if (character === "\u007f" || character === "\b") {
          if (characters.length > 0) {
            characters.pop();
            stdout.write("\b \b");
          }
          continue;
        }
        if (character >= " ") {
          characters.push(character);
          stdout.write("*");
        }
      }
    };

    stdin.on("data", onData);
  });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.some((argument) => argument !== "--stdin")) {
    console.error("사용법: node site/scripts/hash-admin-password.mjs [--stdin]");
    console.error("비밀번호를 명령행 인자로 전달하지 마세요.");
    return 2;
  }

  let password;
  if (stdin.isTTY && !args.includes("--stdin")) {
    password = await readHidden("관리자 비밀번호: ");
    const confirmation = await readHidden("관리자 비밀번호 확인: ");
    if (password !== confirmation) {
      throw new Error("두 비밀번호가 일치하지 않습니다.");
    }
  } else {
    password = await readAllStdin();
  }

  if ([...password].length < 12) {
    throw new Error("관리자 비밀번호는 12자 이상이어야 합니다.");
  }

  const encoded = await hashAdminPassword(password);
  console.log(`ADMIN_PASSWORD_HASH=${encoded}`);
  return 0;
}

try {
  process.exitCode = await main();
} catch (error) {
  console.error(`해시 생성 실패: ${error.message}`);
  process.exitCode = 1;
}
