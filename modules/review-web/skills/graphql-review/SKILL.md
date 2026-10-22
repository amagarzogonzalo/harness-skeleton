---
name: graphql-review
description: GraphQL schema and resolver review. Trigger when a type, field, resolver, mutation, or query cost changes.
---

# GraphQL review

## Schema

- Nullability is a contract. A non-null field that can fail bubbles null to its
  parent; decide whether that is the intended failure mode.
- Use enums for closed sets, input types for mutations, and custom scalars only
  with a documented validation.
- Deprecate before removing. `@deprecated(reason: "...")` needs a migration path
  and a removal date.
- Check the schema diff against the previous version; a removed field is
  breaking even if no code in this repo uses it.

## Resolvers

- Authorization is per field, not only on the root query. Ask: can user A read
  user B's object by guessing an id?
- N+1: a list resolver that queries per item needs a batch loader. Count the
  queries for a realistic query with 100 items.
- Errors: return a typed error in the payload or a GraphQL error with a stable
  code; never leak a stack trace or SQL.
- Mutations: validate input, check authorization, use a transaction, make retries
  idempotent, return the affected object.

## Cost

- Depth limit, cost/complexity limit, alias limit, and a cap on `first`.
- No unbounded list. Cursor pagination with a stable sort.
- Persisted queries or an allowlist for public APIs.
- Introspection off in production unless it is intentional.

## Caching

- Per-user data must not be cached in a shared cache.
- A cache key includes every input that changes the result.
- Invalidate after a mutation; do not serve a stale object indefinitely.

## Verdict

```
FIELD | <type.field> | authz: ok/MISSING | cost: bounded/UNBOUNDED | N+1: yes/no
```

`CRITICAL` for a field-level authz gap; `HIGH` for an unbounded query or N+1 on
a hot path. Do not propose a schema rewrite when a resolver fix is enough.
