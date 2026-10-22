// Show a toast when a session goes idle or fails. Example only.
//
// OpenCode already has its own notifications in most clients. This is useful
// when you run a long task and want a visible signal in the TUI.
//
// Optional: copy to .opencode/plugins/ and restart opencode.

export const Notification = async ({ client }) => ({
  event: async ({ event }) => {
    if (event.type === "session.idle") {
      client.tui
        .showToast({
          body: { title: "session idle", message: "The turn is complete.", variant: "info", duration: 3000 },
        })
        .catch(() => {});
      return;
    }

    if (event.type === "session.error") {
      const error = event.properties?.error;
      const message =
        typeof error === "object" && error && "message" in error
          ? String(error.message)
          : "The session failed.";
      client.tui
        .showToast({
          body: { title: "session error", message: message.slice(0, 900), variant: "error", duration: 8000 },
        })
        .catch(() => {});
    }
  },
});
