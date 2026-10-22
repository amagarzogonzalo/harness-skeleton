// Give compaction the state a fresh context needs, and nothing else.
//
// The default compaction prompt summarizes the conversation. It often loses the
// exact gate status, the files that changed, and the next action. This hook
// appends a short, local, factual block. It does not replace the prompt.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

function readText(path) {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return "";
  }
}

export const CompactionContext = async ({ directory }) => ({
  "experimental.session.compacting": async (_input, output) => {
    const parts = [];

    try {
      const status = execFileSync("git", ["status", "--porcelain"], {
        cwd: directory,
        encoding: "utf8",
      })
        .trim()
        .split("\n")
        .filter(Boolean)
        .slice(0, 40)
        .join("\n");
      parts.push(status ? `Working tree (first 40):\n${status}` : "Working tree: clean");
    } catch {
      parts.push("Working tree: unavailable");
    }

    const marker = readText(join(directory, "artifacts", "gate.json"));
    if (marker) {
      try {
        const data = JSON.parse(marker);
        parts.push(
          `Gate: ok=${data.ok} head=${String(data.head).slice(0, 12)} at=${data.timestamp}`
        );
      } catch {
        parts.push("Gate: marker is not valid JSON");
      }
    } else {
      parts.push("Gate: no marker (make check has not run in this checkout)");
    }

    const checkpoint = readText(join(directory, "artifacts", "checkpoint.md"));
    if (checkpoint) {
      parts.push(`Checkpoint (last 30 lines):\n${checkpoint.trim().split("\n").slice(-30).join("\n")}`);
    }

    parts.push(
      "Preserve: the goal, the files touched, the next concrete action, and any blocker. " +
        "Do not claim progress that the gate does not prove."
    );

    output.context.push(parts.join("\n\n"));
  },
});
