---
name: release-review
description: Release readiness procedure. Trigger before tagging or publishing a release, or when reviewing a release PR.
---

# Release review

## Procedure

1. **Freeze the diff.** List every commit since the last release. Anything that
   is not in the changelog is either missing an entry or should not ship.
2. **Check the version.** Manifest, changelog, tag, and artifact agree. A
   breaking change without a major bump is a blocker.
3. **Walk the migration.** Schema first or code first? Is the old code
   compatible with the new schema during rollout? Is there a down migration?
4. **Name the rollback.** The exact command or flag, who can run it, and what
   state is left behind. "Redeploy the previous image" is only a rollback if the
   schema did not change incompatibly.
5. **Check the flag.** Risky behavior is behind a flag, default off, with an
   owner and a removal date.
6. **Verify the artifact.** Built from the tagged commit, tests run on the
   artifact, checksums/signatures published if the project does that.
7. **Check the observability.** What metric moves if this is broken? What alert
   fires? Who is watching after deploy?
8. **Smoke test.** The smallest end-to-end check that proves the release works.

## Verdict

```
VERSION:    <ok | mismatch: ...>
CHANGELOG:  <complete | missing: ...>
MIGRATION:  <forward+back | forward only | none>
ROLLBACK:   <command/flag | MISSING>
FLAG:       <name/default/owner | not needed>
SMOKE:      <command | MISSING>
```

`BLOCKER` for a missing rollback or an incompatible migration; `HIGH` for an
unlisted breaking change; `MEDIUM` for a missing flag or smoke test. Do not
publish, tag, or deploy as part of the review.
