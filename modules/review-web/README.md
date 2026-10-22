# review-web

Web reviewers for accessibility, frontend quality, GraphQL, and browser
security.

## Agents

| Agent | Finds |
|---|---|
| `accessibility-reviewer` | WCAG 2.2 AA: semantics, keyboard, focus, contrast, ARIA |
| `frontend-reviewer` | Rendering, state, CSS, performance, i18n, hydration |
| `graphql-reviewer` | Schema, nullability, N+1, cost, field authz, pagination |
| `browser-security-reviewer` | XSS, CSP, CSRF, CORS, cookies, postMessage, SRI |

## Skills

- `a11y-review` — keyboard/screen-reader/zoom/contrast procedure.
- `graphql-review` — schema, resolver, cost, and authz checklist.

## Enable

```bash
make enable M=review-web
```

All agents are read-only and mapped to the `review` role. No check script.

## Notes

- The accessibility reviewer needs the rendered UI to be thorough. If it only
  has a diff, it will say which checks it could not perform.
- The frontend reviewer complements `lang-ts`; enable both for a React/TS
  project.
- The browser security reviewer does not replace `security-reviewer`; it goes
  deeper on browser-specific sinks.
