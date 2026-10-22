// Refuse a `git commit` unless the gate evidence is current.
//
// `make check` writes artifacts/gate.json after every check passes. The marker
// is bound to HEAD and to a content hash of the working tree, so editing a file
// after the gate invalidates it. The pre-commit hook re-runs the gate; this hook
// catches the case where the hook is not installed.

import { execFileSync } from "node:child_process";

const COMMIT = /\bgit\s+commit\b/;
const BYPASS = /(--dry-run|--help|-h\b)/;

function runCheck(directory) {
  const attempts = [
    ["uv", ["run", "python", "bin/gate_marker.py", "check"]],
    ["python", ["bin/gate_marker.py", "check"]],
    ["python3", ["bin/gate_marker.py", "check"]],
  ];

  let lastError;
  for (const [command, args] of attempts) {
    try {
      execFileSync(command, args, { cwd: directory, stdio: "pipe" });
      return;
    } catch (error) {
      if (error?.code === "ENOENT") {
        lastError = error;
        continue;
      }
      const detail = error?.stderr?.toString()?.trim();
      throw new Error(
        "blocked: run `make check` before committing." + (detail ? `\n${detail}` : "")
      );
    }
  }

  throw new Error(
    "blocked: cannot verify the gate marker because uv/python was not found on PATH." +
      (lastError ? ` (${lastError.message})` : "")
  );
}

export const CommitGuard = async ({ directory }) => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return;
    const command = String(output?.args?.command ?? "");
    if (!COMMIT.test(command) || BYPASS.test(command)) return;
    runCheck(directory);
  },
});
