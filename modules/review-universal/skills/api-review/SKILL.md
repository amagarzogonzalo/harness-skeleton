---
name: api-review
description: Procedure for reviewing an API change. Trigger when a route, schema, request/response field, status code, or public client contract changes.
---

# API review

## Procedure

1. **Diff the contract.** List every added, removed, or changed field, type,
   default, enum value, header, and status code.
2. **Classify.** Additive and optional is usually safe; removed, renamed,
   narrowed, or newly required is breaking. A new enum value can break a client
   that exhaustively matches.
3. **Trace authorization.** For each new route or field, name the authn check and
   the object-level authz check. A missing one is `CRITICAL`, not a nit.
4. **Trace retries.** For each write, ask what happens if the client retries
   after a timeout. If the answer is "a duplicate", require an idempotency key
   or a natural key.
5. **Check limits.** Page size, request body, query complexity, upload size,
   rate limit. An unbounded endpoint is a denial-of-service surface.
6. **Check errors.** Status code, machine-readable code, message, retryability,
   and whether the error leaks internals.
7. **Check the version path.** If breaking, is there a new version, a deprecation
   window, and a migration note?

## Output

```
CONTRACT:   <change> -> <compatible | breaking>
AUTHZ:      <route> -> <check | MISSING>
IDEMPOTENT: <write> -> <yes | no | unknown>
LIMITS:     <endpoint> -> <bound | UNBOUNDED>
```

A breaking change without a version path is `HIGH`; an authz gap is `CRITICAL`.
Do not propose a full API redesign; name the smallest compatible change.
