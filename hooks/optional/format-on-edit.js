// Format the file after an agent edit. Example only.
//
// Risks: the formatter changes the file after the agent last read it, so the
// agent's diff view is stale. The `formatting` guard suppresses the file.edited
// event caused by the formatter itself, but a slow formatter can still race.
// Prefer a format-on-save in the editor, or `make lint` in the gate.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

import { execFile } from "node:child_process";
import { isAbsolute, join } from "node:path";

const formatting = new Set();

function run(command, args, cwd) {
  return new Promise((resolve) => {
    execFile(command, args, { cwd, timeout: 30_000 }, () => resolve());
  });
}

async function format(file, directory) {
  const path = isAbsolute(file) ? file : join(directory, file);
  const windows = process.platform === "win32";

  if (file.endsWith(".py")) {
    await run(windows ? "ruff.exe" : "ruff", ["format", path], directory);
  } else if (file.endsWith(".rs")) {
    await run(windows ? "rustfmt.exe" : "rustfmt", [path], directory);
  } else if (/\.(ts|tsx|js|jsx|json|css|md)$/.test(file)) {
    await run(windows ? "npx.cmd" : "npx", ["--no-install", "prettier", "--write", path], directory);
  }
}

export const FormatOnEdit = async ({ directory }) => ({
  event: async ({ event }) => {
    if (event.type !== "file.edited") return;
    const file = String(event.properties?.file ?? "");
    if (!file || formatting.has(file)) return;

    formatting.add(file);
    await format(file, directory);
    // Give the formatter's own file.edited event time to arrive and be ignored.
    setTimeout(() => formatting.delete(file), 1000);
  },
});
