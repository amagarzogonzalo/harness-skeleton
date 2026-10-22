// Warn on `console.log`/`console.debug` left in application code. It does not
// block: debugging with a log is legitimate, and the gate should not turn every
// edit into an argument. The warning is enough to catch the one that ships.
//
// Opt-in: `uv run python bin/modules.py enable lang-ts --with-hooks`.

import { readFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";

const seen = new Set();

export const NoConsole = async ({ directory, client }) => ({
  event: async ({ event }) => {
    if (event.type !== "file.edited") return;

    const file = String(event.properties?.file ?? "");
    if (!/\.(ts|tsx|js|jsx|mjs|cjs)$/.test(file)) return;
    if (/(^|[\\/])(test|tests|__tests__|spec|scripts|config)([\\/]|$)/.test(file)) return;
    if (seen.has(file)) return;

    const path = isAbsolute(file) ? file : join(directory, file);
    let text;
    try {
      text = readFileSync(path, "utf8");
    } catch {
      return;
    }

    if (!/console\.(log|debug)\s*\(/.test(text)) return;
    seen.add(file);

    try {
      await client.tui.showToast({
        body: {
          title: "ts: console.log",
          message: `${file} contains console.log/debug. Remove it before shipping.`,
          variant: "warning",
          duration: 6000,
        },
      });
    } catch {
      // Headless run: no TUI to notify. Do not fail the edit.
    }
  },
});
