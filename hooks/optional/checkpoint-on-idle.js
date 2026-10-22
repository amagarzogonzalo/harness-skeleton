// Write a small idle marker when a session goes idle. Example only.
//
// This cannot see the conversation, so it is not a checkpoint: it is a
// heartbeat that other tooling (or a human) can use to notice a stalled run.
// The real checkpoint procedure is skills/checkpoint/SKILL.md.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export const IdleMarker = async ({ directory }) => ({
  event: async ({ event }) => {
    if (event.type !== "session.idle") return;
    try {
      const dir = join(directory, "artifacts");
      mkdirSync(dir, { recursive: true });
      writeFileSync(
        join(dir, "last-idle.json"),
        JSON.stringify({ sessionID: event.properties?.sessionID, at: new Date().toISOString() }) + "\n",
        "utf8"
      );
    } catch {
      // Never fail a turn because a marker could not be written.
    }
  },
});
