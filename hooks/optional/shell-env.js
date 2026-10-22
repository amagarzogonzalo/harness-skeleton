// Add a few non-secret environment variables to every shell invocation.
//
// Do not put credentials here. The plugin source is committed and runs in the
// same process as the agent. If a tool needs a secret, read it from the
// environment that opencode was started with, or from a secret manager.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

export const ShellEnv = async () => ({
  "shell.env": async (_input, output) => {
    output.env.HARNESS = "1";
    output.env.PYTHONUNBUFFERED = "1";
    output.env.UV_NO_PROGRESS = "1";
  },
});
