# 3. Backup types: full, differential, incremental

## What is it?

| Type | Copies | Size | Restore needs |
|---|---|---|---|
| **Full** | every file | large | just this backup (+ WAL) |
| **Differential (diff)** | files changed since the last **full** | medium, grows during the week | the full + this diff |
| **Incremental (incr)** | files changed since the last backup **of any type** | small | the full + the latest diff + every incr after it |

All three are **physical** backups: copies of the database files, not SQL dumps.

## Why this project uses all three

It is a trade-off between backup cost and restore speed:

- Full backups every hour would be safe but huge and slow.
- One full backup and only incrementals for months would be small, but a restore would have to chain hundreds of pieces.

The classic schedule used here: **weekly full, daily differential, hourly incremental**. A restore then needs at most one full, one diff and a handful of incrementals, plus the WAL since the last of them.

**Alternatives:** only full backups (simplest, fine for small databases), only incrementals with periodic "synthetic fulls" (some tools), storage snapshots.

## How it works

### Block incremental and bundles
Newer pgBackRest versions can store only the **changed blocks** of a file, not the whole file (`repo1-block=y`). That makes incrementals of large tables much smaller. **Bundling** (`repo1-bundle=y`) packs many small files into a few larger objects, which matters for object storage (fewer requests, lower cost).

### Retention
`repo1-retention-full=2` keeps the last **two** full backups and everything that depends on them. When a third full backup finishes, the oldest full, its diffs and incrementals, and the WAL only they needed are deleted (`expire`). Two fulls means you can go back one to two weeks.

### Backup labels
Each backup has a label that shows its type and parents:

```
20261003-020928F                     full
20261003-020928F_20261003-021255I    incremental on top of that full
```

## Where it is integrated

The schedule is in [`image/crontab`](../image/crontab):

```
# Weekly full, daily differential, hourly incremental: restore = 1 full + 1 diff + a few incr + WAL.
0 1 * * 0     run-backup full
0 1 * * 1-6   run-backup diff
30 * * * *    run-backup incr
```

The options are written into the backup host's pgBackRest configuration by [`image/bin/entrypoint`](../image/bin/entrypoint):

```ini
repo1-retention-full=${RETENTION_FULL:-2}
repo1-bundle=y
repo1-block=y
compress-type=zst
```

[`image/bin/run-backup`](../image/bin/run-backup) runs one backup and reports the result to Prometheus, success or not:

```bash
pgbackrest --stanza="$STANZA" --type="$type" backup
rc=$?
...
backup_last_run_success $(( rc == 0 ? 1 : 0 ))
```

## Try it

```bash
scripts/backup.sh incr      # take an incremental now
scripts/backup.sh diff
scripts/status.sh           # pgbackrest info: every backup, its size and what it depends on
```

In the `info` output, compare `database size` with `repo1: backup size`: an incremental of a quiet database is tiny.

## Common mistakes

- **Deleting "old" fulls by hand.** Diffs and incrementals depend on them. Let `expire` do it.
- **Retention too short for your needs.** With `retention-full=2` and weekly fulls you cannot go back three weeks. Decide how far back you must be able to go, then set retention.
- **Only checking that backups run.** A backup that runs is not a backup that restores. That is chapter 6.

## Check yourself

1. Restoring Thursday afternoon with this schedule needs which backups?
2. Why is `repo1-bundle=y` useful on object storage?
3. What happens to the WAL of a full backup that retention removes?

<details><summary>Answers</summary>

1. Sunday's full, Thursday's 01:00 differential, the incrementals after it up to the afternoon, then the archived WAL since the last incremental.
2. Object storage charges and waits per request; thousands of small files become a few large objects, so backups and restores are faster and cheaper.
3. WAL needed only by expired backups is removed too, so the repository does not grow forever.

</details>

Next: [pgBackRest](04-pgbackrest.md)
