# 2. WAL, archiving and point-in-time recovery

## What is it?

The **WAL (write-ahead log)** is PostgreSQL's diary. Before PostgreSQL changes any data file, it first writes a record of the change into the WAL. If the server crashes, PostgreSQL replays the WAL on the next start and loses nothing that was committed.

**WAL archiving** copies every finished WAL file somewhere safe. **Point-in-time recovery (PITR)** uses a base backup plus the archived WAL to rebuild the database **as it was at any moment you choose**, to the second.

## Why this project uses it

A nightly backup alone means you can lose up to a day of orders. With continuous WAL archiving, the backup repository receives every change within about a minute. That is the difference between "we lost today's sales" and "we lost the last minute".

PITR is also the cure for **human mistakes**. If someone runs `DROP TABLE orders` at 15:00:03, you restore to 15:00:02 and the table is back with every order up to that second.

**Alternatives:** streaming replication to a standby server (protects against hardware failure, but a `DROP TABLE` is replicated instantly too, so it is not a backup), `pg_dump` every night (no PITR), storage snapshots (fast, but usually not point-in-time and not tested).

## How it works

### WAL segments
The WAL is written in files called **segments**, 16 MiB each, with names like `000000010000000000000005`:

```
00000001 00000000 00000005
timeline  "log"   segment
```

When a segment is full (or forced to switch), PostgreSQL calls the **`archive_command`** for it. Only when that command succeeds is the segment considered archived; until then PostgreSQL keeps it on its own disk and retries.

### archive_timeout: bounding data loss
A quiet database might take hours to fill 16 MiB, and changes in an unfinished segment are not archived yet. `archive_timeout=60` forces a segment switch at least every 60 seconds when there were changes. That gives an RPO of about one minute.

### Recovery targets
A restore copies a base backup, then replays archived WAL:
- **to the end** (`--type=default`): as recent as possible, used by the restore drill
- **to a time** (`--type=time --target="2026-10-03 15:00:02+00"`): stops just before the first commit after that time, used to undo a mistake

### Timelines
After a point-in-time recovery, the database's history **forks**: the old future (with the mistake) and the new one. PostgreSQL gives the new branch a new **timeline** number (1 → 2) and writes a small `.history` file to the archive, so WAL from the two branches is never mixed up. You can see it in segment names: `00000002...`.

### pg_stat_archiver
PostgreSQL counts archived and failed attempts in the view `pg_stat_archiver`. This project's monitoring reads it to know whether archiving works (chapter 9).

## Where it is integrated

[`deploy/compose.yaml`](../deploy/compose.yaml), the `db` service:

```yaml
command:
  - postgres
  - -c
  - wal_level=replica
  - -c
  - archive_mode=on
  - -c
  - archive_command=pgbackrest --stanza=main archive-push %p
  # Send a WAL segment to the backup host at least every 60 s, even when traffic is low:
  # this bounds how much recent data a restore can lose.
  - -c
  - archive_timeout=60
```

`%p` is replaced by the path of the finished segment. `pgbackrest archive-push` sends it to the backup host (chapter 4).

Point-in-time recovery is scripted in [`scripts/pitr.sh`](../scripts/pitr.sh):

```bash
log "1/4 Archiving the latest changes"
if sql "select pg_switch_wal()" >/dev/null 2>&1; then
  on_backup pgbackrest --stanza=main check >/dev/null || die "WAL could not be archived; refusing to restore"
...
compose run --rm --no-deps -e ROLE=restore db --type=time "--target=$target" --target-action=promote
```

Step 1 is easy to forget and very important: the changes just before the mistake are still in the **current, unarchived** segment. `pg_switch_wal()` closes that segment and `pgbackrest check` waits until it is in the archive. Without it, the last minute before the mistake would be lost.

## Try it

```bash
# see how archiving is doing
docker compose -f deploy/compose.yaml exec -u postgres db psql -d shop -c \
  "select archived_count, failed_count, last_archived_wal, last_archived_time from pg_stat_archiver"

# force a segment switch and watch last_archived_wal change a few seconds later
docker compose -f deploy/compose.yaml exec -u postgres db psql -d shop -c "select pg_switch_wal()"

# the WAL files in the repository
docker compose -f deploy/compose.yaml exec -u postgres backup pgbackrest --stanza=main repo-ls --recurse archive
```

The full "drop a table and get it back" exercise is lab 3 in [Hands-on labs](13-hands-on-labs.md).

## Common mistakes

- **Archiving without a base backup.** WAL alone is useless; you need a backup to replay it onto.
- **No `archive_timeout`.** On a quiet database, "continuous" archiving may be hours behind.
- **Ignoring archive failures.** When `archive_command` keeps failing, WAL piles up on the database disk until it is full and the database stops. Alert on it (this project does: `WalArchivingFailing`).
- **Restoring to a time without archiving the current segment first.** The minutes just before the target are lost.
- **Choosing a target time in the wrong time zone.** Always write the offset (`+00`).

## Check yourself

1. Why is a replica (standby server) not a backup?
2. What does `archive_timeout=60` guarantee, and what does it cost?
3. Why does PostgreSQL create a new timeline after a point-in-time recovery?

<details><summary>Answers</summary>

1. It copies every change immediately, including mistakes like `DROP TABLE`. A backup lets you go back in time.
2. At most about 60 seconds of committed changes are not yet archived (the RPO). The cost: more, partly empty WAL files when traffic is low (they compress very well).
3. The database's history forks at the target. The new timeline keeps WAL from the old future (after the mistake) and the new future apart, so a later restore never mixes them.

</details>

Next: [Backup types](03-backup-types.md)
