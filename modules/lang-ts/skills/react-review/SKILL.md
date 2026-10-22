---
name: react-review
description: React review procedure for hooks, effects, state, rendering, accessibility, and server/client boundaries. Trigger when reviewing or changing React components.
---

# React review

## Hooks

- Hooks are called unconditionally, at the top level. A hook after an early
  return is a bug.
- Every value read inside `useEffect` is in the dependency array, or is stable
  by construction. Do not disable the lint rule to silence a stale closure.
- `useEffect` is for synchronization with an external system, not for deriving
  state from props. Derive during render instead.
- Cleanup every subscription, timer, listener, and fetch (with `AbortController`).

## State

- One source of truth. Do not copy props into state unless the prop is an
  initial value and the copy is intentionally uncontrolled.
- Use the updater form when the next state depends on the previous:
  `setCount(c => c + 1)`.
- Lift state only as far as the nearest common ancestor. Context is for
  low-frequency values; a context that changes every render re-renders the tree.
- A reducer is better than five `useState`s that change together.

## Rendering

- Keys must be stable and unique. `index` is wrong for reorderable lists.
- `cond && <X />` renders `0` when `cond` is `0`; use `cond ? <X /> : null`.
- No `Date.now()`, `Math.random()`, or `window` access during render; it breaks
  hydration and makes output non-deterministic.
- `dangerouslySetInnerHTML` requires sanitization (DOMPurify or equivalent) and
  a reason. Prefer rendering text.

## Server/client

- `"use client"` marks a boundary; put it as low as possible.
- Never import a server-only module (DB, secrets, `fs`) into a client component.
- Server actions and route handlers need their own authorization check. A
  hidden button is not an authorization check.
- Do not pass secrets to the client, including `NEXT_PUBLIC_*`/`VITE_*` values.

## Accessibility

- Use semantic elements: `button`, `a`, `label`, `dialog`.
- Every input has a label. Every image has `alt` (or `alt=""` if decorative).
- Keyboard: focus visible, focus order logical, Escape closes overlays.
- Do not use color alone to convey state. Check contrast.
- Test with the keyboard, not only with a mouse.

## Tests

- Use Testing Library: `getByRole`, `getByLabelText`, `findByText`.
- Assert what the user sees, not component internals or state variables.
- `await` async UI changes; do not assert immediately after an interaction.
- A snapshot of a whole component is not a behavior test.

## Performance

- Measure before memoizing. `useMemo`/`useCallback` with a new dependency every
  render is worse than nothing.
- Virtualize long lists; paginate large tables.
- Keep client components small; move data fetching to the server where possible.
