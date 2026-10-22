// Run `tsc --noEmit` shortly after a TypeScript file changes, debounced so a
// burst of edits produces one check. This is deliberately opt-in: on a large
// project it is slower than the edit loop and duplicates the gate.
//
// Opt-in: `uv run python bin/modules.py enable lang-ts --with-hooks`.

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

let timer;

function typecheck(directory, client) {
  execFile(
    process.platform === "win32" ? "npx.cmd" : "npx",
    ["--no-install", "tsc", "--noEmit"],
    { cwd: directory, timeout: 60_000 },
    (error, _stdout, stderr) => {
      if (!error) return;
      const detail = String(stderr || error.message).trim().split("\n").slice(0, 8).join("\n");
      client.tui
        .showToast({
          body: {
            title: "tsc --noEmit",
            message: detail.slice(0, 900) || "type check failed",
            variant: "error",
            duration: 10_000,
          },
        })
        .catch(() => {});
    }
  );
}

export const TypecheckOnEdit = async ({ directory, client }) => ({
  event: async ({ event }) => {
    if (event.type !== "file.edited") return;
    const file = String(event.properties?.file ?? "");
    if (!/\.(ts|tsx)$/.test(file)) return;
    if (!existsSync(join(directory, "tsconfig.json"))) return;

    clearTimeout(timer);
    timer = setTimeout(() => typecheck(directory, client), 1500);
  },
});
