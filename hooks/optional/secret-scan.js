// Block high-confidence secret patterns before they reach a file or a shell.
//
// This is deliberately narrow. Generic "password =" patterns produce false
// positives on examples and tests, and a guard that cries wolf is disabled.
// The repository's `env-protection` hook blocks secret *paths*; this one blocks
// secret *values*.
//
// Optional: copy to .opencode/plugins/ and restart opencode. Review the
// patterns against your stack first.

const PATTERNS = [
  ["aws-access-key", /\bAKIA[0-9A-Z]{16}\b/],
  ["private-key", /-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/],
  ["github-token", /\bgh[pousr]_[A-Za-z0-9]{36,}\b/],
  ["openai-key", /\bsk-[A-Za-z0-9_-]{20,}\b/],
  ["anthropic-key", /\bsk-ant-[A-Za-z0-9_-]{20,}\b/],
  ["slack-token", /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/],
  ["google-api-key", /\bAIza[0-9A-Za-z_-]{35}\b/],
  ["stripe-key", /\b(sk|rk)_(live|test)_[A-Za-z0-9]{20,}\b/],
];

function findSecret(text) {
  for (const [name, pattern] of PATTERNS) {
    if (pattern.test(text)) return name;
  }
  return null;
}

export const SecretScan = async () => ({
  "tool.execute.before": async (input, output) => {
    let text = "";
    if (input.tool === "write" || input.tool === "edit") {
      text = String(output?.args?.content ?? output?.args?.newString ?? "");
    } else if (input.tool === "bash") {
      text = String(output?.args?.command ?? "");
    } else {
      return;
    }

    const name = findSecret(text);
    if (name) {
      throw new Error(
        `blocked: a ${name} pattern was found in ${input.tool} input. ` +
          "Use an environment variable or a secret manager; never write the value."
      );
    }
  },
});
