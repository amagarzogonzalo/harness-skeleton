// Append every permission request and reply to artifacts/permissions.log.
//
// This is an audit trail, not an approval mechanism. It never changes
// output.status; an auto-approve hook is exactly the anti-pattern this harness
// avoids. The log is gitignored and local.

import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

function record(directory, event) {
  try {
    const dir = join(directory, "artifacts");
    mkdirSync(dir, { recursive: true });
    appendFileSync(
      join(dir, "permissions.log"),
      JSON.stringify({ at: new Date().toISOString(), ...event }) + "\n",
      "utf8"
    );
  } catch {
    // An audit log failure must never block the tool. The tool call is already
    // visible in the session; this is a secondary record.
  }
}

export const PermissionAudit = async ({ directory }) => ({
  "permission.ask": async (input) => {
    record(directory, {
      event: "asked",
      id: input.id,
      type: input.type,
      title: input.title,
      pattern: input.pattern,
      sessionID: input.sessionID,
    });
  },

  event: async ({ event }) => {
    if (event.type !== "permission.replied") return;
    record(directory, {
      event: "replied",
      sessionID: event.properties?.sessionID,
      permissionID: event.properties?.permissionID,
      response: event.properties?.response,
    });
  },
});
