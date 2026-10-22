// Block a bare `except:` in Python edits. It catches KeyboardInterrupt and
// SystemExit, and it hides the exception type from the reader. `except
// Exception as exc:` is not blocked: it is often correct when the error is
// logged and re-raised or converted.
//
// Opt-in: run `make enable M=lang-python` with `--with-hooks` to load it.

const BARE_EXCEPT = /^\s*except\s*:/m;

export const NoBareExcept = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "write" && input.tool !== "edit") return;
    const path = String(output?.args?.filePath ?? "");
    if (!path.endsWith(".py")) return;

    const text = String(output?.args?.content ?? output?.args?.newString ?? "");
    if (BARE_EXCEPT.test(text)) {
      throw new Error(
        `blocked: bare \`except:\` in ${path}. Catch the specific exception, ` +
          "or `except Exception as exc:` and log/re-raise it."
      );
    }
  },
});
