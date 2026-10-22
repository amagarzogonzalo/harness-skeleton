---
name: threat-model
description: Build a threat model for a feature or diff. Trigger when a change adds an entry point, crosses a trust boundary, handles credentials, or touches payments/PII.
---

# Threat model

## 1. Draw the system

```
[user/browser] -> [API] -> [DB]
                     |-> [queue] -> [worker] -> [third party]
                     |-> [LLM] -> [tool] -> [filesystem/network]
```

Mark every trust boundary. Data crossing a boundary is untrusted until validated
on the other side.

## 2. List assets and entry points

- Assets: credentials, sessions, PII, money, permissions, availability, audit
  integrity.
- Entries: routes, webhooks, queue messages, file uploads, CLI args, env vars,
  model output, third-party callbacks.

## 3. STRIDE each boundary

| Threat | Ask |
|---|---|
| Spoofing | Can the caller prove who it is? |
| Tampering | Can the data be changed in transit or at rest? |
| Repudiation | Is the action attributable? |
| Information disclosure | Can another tenant/user read it? |
| Denial of service | Is the work bounded? |
| Elevation of privilege | Can a user reach an admin action? |

## 4. Controls

For each threat, name the control and its state: `present`, `missing`, or
`untested`. A control with no test is `untested`.

## 5. Residual risk

What remains after the control? Who accepts it? A threat model with no residual
risk is usually a model that stopped too early.

## Output

```
THREAT | STRIDE | path | impact | control | residual | owner
```

Rank by impact x likelihood. Do not list a threat without an entry point.
