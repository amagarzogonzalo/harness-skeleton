---
name: migration-review
description: Review or design a schema/data migration. Trigger when a table, column, index, constraint, or backfill changes, especially on a live system.
---

# Migration review

## Expand / contract

A migration is safe only if old and new code can run at the same time.

1. **Expand.** Add the new column/table/index as nullable/optional. No code
   depends on it yet.
2. **Dual write.** New code writes both old and new shapes. Old code still works.
3. **Backfill.** Batched, idempotent, resumable, rate-limited. Verify with
   counts/checksums.
4. **Switch reads.** New code reads the new shape. Keep the old write for
   rollback.
5. **Contract.** After the rollback window, drop the old column/table and the
   dual write.

Never skip from expand to contract in one deploy on a live system.

## Checklist

- [ ] The migration runs while the old code is still serving traffic.
- [ ] No table rewrite/long lock on a hot table; `CREATE INDEX CONCURRENTLY`
      where supported.
- [ ] Backfill is batched and has a stop switch.
- [ ] Re-running is idempotent.
- [ ] Down migration or forward fix is written and tested.
- [ ] Constraints enforce the new invariant, not only application code.
- [ ] Progress/error/replication-lag metrics exist.
- [ ] Verification query is written before the migration runs.
- [ ] The migration user is not a superuser.
- [ ] A rollback window and owner are named.

## Output

```
STEP | compatible | lock/backfill | rollback | verify
```

`BLOCKER` for a destructive change with no rollback; `HIGH` for an unbatched
backfill; `MEDIUM` for a missing verification query.
