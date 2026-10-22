// Block secret-bearing paths at the tool boundary.
//
// `opencode.json` denies `read`/`edit` on the same patterns, but permissions are
// a policy layer and bash can route around them (`rg KEY .env`). This hook backs
// the policy with a runtime check for the read, write, edit, and bash tools.
// It is a guardrail, not a sandbox: code run through `python -c` can still open
// the file. That limitation is documented in .opencode/rules/security.md.

const EXEMPT = /^\.env\.(example|sample|template|dist)$/i;

function baseName(path) {
  const parts = String(path).split(/[\\/]+/);
  return parts[parts.length - 1] || "";
}

function isSecretPath(path) {
  const value = String(path);
  const base = baseName(value);
  if (EXEMPT.test(base)) return false;

  if (base === ".env" || base === ".envrc" || /^\.env\./i.test(base)) return true;
  if (/\.pem$/i.test(base)) return true;
  if (/credentials/i.test(base)) return true;
  if (/^id_(rsa|ed25519|ecdsa|dsa)$/i.test(base)) return true;

  const normalized = value.replace(/\\/g, "/");
  return /(^|\/)\.ssh(\/|$)/.test(normalized) || /(^|\/)\.aws(\/|$)/.test(normalized);
}

const ACCESS_COMMAND =
  /(^|[;&|]\s*)(cat|type|head|tail|less|more|rg|grep|Select-String|Get-Content|git\s+(show|diff|log|add|checkout|restore))\b/i;

function bashTouchesSecret(command) {
  const text = String(command);
  if (!ACCESS_COMMAND.test(text)) return false;

  // Split on shell whitespace and separators. Quoted paths with spaces are not
  // handled perfectly, but every common read of a secret file is caught.
  const tokens = text.split(/[\s"'`<>|;&()]+/).filter(Boolean);
  if (tokens.some(isSecretPath)) return true;

  // Catch `git show HEAD:.env` and similar suffix forms.
  return /(^|[\\/\s"'`=:])\.env(\.(?!example|sample|template|dist)[\w.-]*)?($|[\s"'`;|&)])/i.test(text);
}

function deny(path) {
  throw new Error(
    `blocked: ${path} is a secret-bearing path. ` +
      "Read the example/template file instead, or ask the human to provide the value."
  );
}

export const EnvProtection = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool === "read" || input.tool === "write" || input.tool === "edit") {
      const path = output?.args?.filePath;
      if (typeof path === "string" && isSecretPath(path)) deny(path);
      return;
    }

    if (input.tool === "bash") {
      const command = output?.args?.command;
      if (typeof command === "string" && bashTouchesSecret(command)) {
        deny("the command references a secret file");
      }
    }
  },
});

export { isSecretPath, bashTouchesSecret };
