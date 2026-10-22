// Nudge, do not block: `unwrap()` in library code is a panic waiting for a
// caller. Blocking every unwrap would also block tests and prototypes, so this
// hook shows a toast after the edit. The gate's clippy config can enforce
// `clippy::unwrap_used` where the project wants a hard rule.
//
// Opt-in: `uv run python bin/modules.py enable lang-rust --with-hooks`.

import { readFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";

const seen = new Set();

export const NoUnwrap = async ({ directory, client }) => ({
  event: async ({ event }) => {
    if (event.type !== "file.edited") return;

    const file = String(event.properties?.file ?? "");
    if (!file.endsWith(".rs") || /(^|[\\/])tests?([\\/]|$)/.test(file)) return;
    if (seen.has(file)) return;

    const path = isAbsolute(file) ? file : join(directory, file);
    let text;
    try {
      text = readFileSync(path, "utf8");
    } catch {
      return;
    }

    if (!/\.(unwrap|expect)\s*\(/.test(text)) return;
    seen.add(file);

    try {
      await client.tui.showToast({
        body: {
          title: "rust: unwrap/expect",
          message: `${file} uses unwrap/expect outside tests. Prefer `?` or a typed error.`,
          variant: "warning",
          duration: 6000,
        },
      });
    } catch {
      // The TUI may not be attached (headless run). The edit is already done;
      // a failed notification must not fail the tool.
    }
  },
});
