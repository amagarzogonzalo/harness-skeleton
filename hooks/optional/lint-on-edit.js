// Lint the edited file and show the first lines in a toast. Example only.
//
// This duplicates the gate and can be slow (Rust clippy runs on the crate). Use
// it for fast feedback in a small project, not as a replacement for `make check`.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

import { execFile } from "node:child_process";
import { isAbsolute, join } from "node:path";

function lint(file, directory) {
  const path = isAbsolute(file) ? file : join(directory, file);
  const windows = process.platform === "win32";

  if (file.endsWith(".py")) {
    return [windows ? "ruff.exe" : "ruff", ["check", "--output-format", "concise", path]];
  }
  if (/\.(ts|tsx|js|jsx)$/.test(file)) {
    return [windows ? "npx.cmd" : "npx", ["--no-install", "eslint", path]];
  }
  if (file.endsWith(".rs")) {
    return [windows ? "cargo.exe" : "cargo", ["clippy", "--message-format", "short"]];
  }
  return null;
}

export const LintOnEdit = async ({ directory, client }) => ({
  event: async ({ event }) => {
    if (event.type !== "file.edited") return;
    const file = String(event.properties?.file ?? "");
    const command = lint(file, directory);
    if (!command) return;

    execFile(command[0], command[1], { cwd: directory, timeout: 60_000 }, (error, _out, stderr) => {
      if (!error) return;
      const detail = String(stderr || error.message).trim().split("\n").slice(0, 6).join("\n");
      client.tui
        .showToast({
          body: {
            title: `lint: ${file}`,
            message: detail.slice(0, 900) || "lint failed",
            variant: "warning",
            duration: 8000,
          },
        })
        .catch(() => {});
    });
  },
});
