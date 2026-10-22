// Block a small set of commands whose blast radius is not worth a prompt.
//
// `opencode.json` already denies most of these. This hook exists for the cases
// where a command is inside a compound shell line, and to give a clearer error
// than "permission denied". It is not a sandbox: a script can still do damage.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

const RULES = [
  [/\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(\/|~|\$HOME)(\s|$)/, "recursive delete of / or home"],
  [/\brm\s+-rf\s+\*/i, "recursive delete with a wildcard"],
  [/:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:/, "fork bomb"],
  [/\bmkfs(\.\w+)?\b/, "filesystem format"],
  [/\bdd\s+if=.*\bof=\/dev\//, "raw device write"],
  [/\bchmod\s+-R\s+777\s+\//, "world-writable root"],
  [/\b(curl|wget)\b[^|;]*\|\s*(sh|bash|zsh)\b/, "pipe download to shell"],
  [/\bdocker\s+run\b[^;]*--privileged\b/, "privileged container"],
  [/\bgit\s+push\b[^;]*(\s-f\b|\s--force\b)/, "force push"],
  [/\bterraform\s+destroy\b/, "terraform destroy"],
  [/\bkubectl\s+delete\s+(ns|namespace)\b/, "delete a namespace"],
  [/\bDROP\s+DATABASE\b/i, "drop database"],
  [/\bTRUNCATE\s+TABLE\b/i, "truncate table"],
];

export const DangerousCommand = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return;
    const command = String(output?.args?.command ?? "");
    for (const [pattern, reason] of RULES) {
      if (pattern.test(command)) {
        throw new Error(`blocked: ${reason}. Run it yourself if it is intended.`);
      }
    }
  },
});
