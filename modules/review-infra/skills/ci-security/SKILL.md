---
name: ci-security
description: GitHub Actions security review. Trigger when editing a workflow, adding an action, or changing permissions, secrets, or triggers.
---

# CI security

## Procedure

1. **List triggers.** For each, ask: who can cause this to run, and with which
   secrets? `pull_request` from a fork has no secrets; `pull_request_target`
   does, and is dangerous the moment it checks out the PR head.
2. **Set permissions.** Top-level `permissions: contents: read`; elevate per job
   only. `id-token: write` only for OIDC.
3. **Pin actions.** Full commit SHA for third-party actions. A tag is mutable.
   Check the action's repository and publisher, not only its name.
4. **Find injection sinks.** `${{ github.event.pull_request.title }}`, branch
   names, commit messages, issue bodies, labels. Pass them through `env:` and
   quote, never inline in `run:`.
5. **Trace secrets.** Which jobs receive them? Are they exposed to fork code?
   Are they printed? Are they passed to a third-party action?
6. **Check cache.** Key includes lockfile hash + OS. A fork cannot write a cache
   that main trusts. Do not cache executables that are then run unverified.
7. **Check artifacts.** Name collisions, untrusted upload, download without
   verification, retention.
8. **Check runners.** Self-hosted on a public repo is RCE. Prefer ephemeral.
9. **Check failure behavior.** A security job with `continue-on-error`, a
   required check that can be skipped, `if: always()` on a deploy.

## Safe pattern

```yaml
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>
      - run: make check
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}  # data, not code
```

## Verdict

```
TRIGGER | <event> | secrets: yes/no | untrusted code: yes/no
PERM | <job> | <permissions> | <needed?>
PIN | <action> | <sha/tag>
INJECTION | <file:line> | <source> | <sink>
```

`CRITICAL` for `pull_request_target` + checkout of PR head + secrets, or a
workflow-injection sink. `HIGH` for write-all or an unpinned third-party action.
