# 13. Hands-on labs

Start the stack once with `scripts/up.sh` (it waits for the first full backup). All commands run from the repository root, in bash (Git Bash on Windows). To save typing:

```bash
dc() { docker compose -f deploy/compose.yaml "$@"; }
sql() { dc exec -T -u postgres db psql -d shop -XAtc "$1"; }
```

Compare your numbers with [`docs/test-results.md`](../docs/test-results.md).

## Lab 1: Explore

1. `dc ps`: which services are running, which are healthy? Which one has exited, and why is that fine?
2. `scripts/status.sh`: how many backups exist, of which types? What is the database size vs the backup size?
3. `sql "select count(*), max(created_at) from orders"` twice, 10 seconds apart. How many orders per second does the app write?
4. `dc exec db cat /etc/pgbackrest/pgbackrest.conf` and `dc exec backup cat /etc/pgbackrest/pgbackrest.conf`. Which one has `repo1-s3-key`? Why?
5. Open Grafana (http://localhost:3000) and Prometheus (http://localhost:9090 → Alerts).

## Lab 2: Run a drill and read it

```bash
scripts/drill.sh
```

1. Find each of the five steps in the output.
2. How long did the restore take, and how long the whole drill (RTO)?
3. How many seconds behind the live database was the restored copy (RPO)? Why is it usually below about 60 s?
4. Run `scripts/backup.sh incr` and then the drill again. Did anything change?

## Lab 3: The accident: drop a table, get it back

```bash
T="$(sql "select to_char(clock_timestamp() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS.US') || '+00'")"
BEFORE="$(sql "select count(*) from orders where created_at <= '$T'")"
echo "target=$T orders=$BEFORE"
sleep 3
sql "drop table orders"                    # the mistake
scripts/pitr.sh "$T"                        # type 'restore' to confirm
sql "select count(*) from orders where created_at <= '$T'"   # must equal $BEFORE
sql "select timeline_id from pg_control_checkpoint()"         # a new timeline
```

1. How long did the recovery take from start to finish?
2. Why does `pitr.sh` run `pg_switch_wal()` and `pgbackrest check` *before* stopping the database?
3. Take a new full backup (`scripts/backup.sh full`) and run a drill. Does it pass on the new timeline?

## Lab 4: Storage outage

```bash
dc stop s3
sleep 60; sql "select archived_count, failed_count from pg_stat_archiver"
```

1. Is the application still writing orders? (Count them twice.)
2. Wait until Prometheus shows **WalArchivingFailing** (Alerts tab). How long did it take, and why not immediately? (Look at `for:` in the rule.)
3. `dc start s3`. How long until `last_archived_time` is recent again?
4. Run `scripts/backup.sh incr` and `scripts/drill.sh`. Are any orders missing?

## Lab 5: Bit rot: a backup file is damaged in storage

The object store's internal filer API (port 8888) lets you replace a file directly, simulating damaged storage. Find the first bundle of the newest full backup, damage 4 KiB in the middle, and keep a copy:

```bash
LABEL="$(dc exec -T -u postgres backup sh -c "pgbackrest --stanza=main info --output=json | python3 -c 'import json,sys; print([b[\"label\"] for b in json.load(sys.stdin)[0][\"backup\"] if b[\"type\"]==\"full\"][-1])'")"
F="/buckets/pgbackrest/main/backup/main/$LABEL/bundle/1"
dc exec -T s3 sh -c "curl -fsS -o /tmp/orig http://localhost:8888$F && cp /tmp/orig /tmp/rot \
  && dd if=/dev/urandom of=/tmp/rot bs=4096 seek=50 count=1 conv=notrunc && curl -fsS -o /dev/null -F file=@/tmp/rot http://localhost:8888$F"
scripts/verify.sh       # what does it report?
scripts/drill.sh        # which step fails?
```

1. Which alerts fire?
2. Put the original back: `dc exec -T s3 sh -c "curl -fsS -o /dev/null -F file=@/tmp/orig http://localhost:8888$F"`, then verify and drill again.
3. Without the nightly verify and drill, when would you have noticed?

## Lab 6: The lost encryption key

```bash
dc exec -T -e PGBACKREST_REPO1_CIPHER_PASS=not-the-real-key backup restore-drill
scripts/drill.sh
```

1. What error does the first drill show?
2. Where would you keep the real passphrase so that losing the backup host does not lose the backups?

## Lab 7: Change a parameter

Pick one:
- **RPO:** change `archive_timeout=60` to `archive_timeout=300` in [`deploy/compose.yaml`](../deploy/compose.yaml), run `dc up -d db`, wait 10 minutes, run a few drills. How does the data loss number change? Put it back.
- **Retention:** set `RETENTION_FULL: "1"` in the `backup` service's environment, run `dc up -d backup`, take two full backups (`scripts/backup.sh full` twice) and look at `scripts/status.sh`. What did `expire` delete? Put it back.

## Lab 8: Test the tests

1. In [`deploy/prometheus/rules/backups.yml`](../deploy/prometheus/rules/backups.yml), change `WalArchivingFailing`'s expression to `pg_stat_archiver_failed_count > 0`.
2. Run the rule tests:

   ```bash
   docker run --rm -v "$PWD:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules backups.test.yml
   ```

3. Which test fails, and what real-life problem does it describe? Revert the change and run the tests again.
4. Bonus: in [`image/bin/backup-metrics`](../image/bin/backup-metrics), make `wal_segment_number` return `0` and run `python -m pytest tests`. Which test catches it?

## Lab 9: The disk is gone: rebuild the database from the backups

The worst day: the database's data volume is lost (failed disk, deleted volume, new server).

```bash
scripts/status.sh                         # note how many backups exist
docker compose -f deploy/compose.yaml exec -u postgres db psql -d shop -Atc "select count(*) from orders"
scripts/recover-lost-db.sh                # type 'recover': deletes the volume, restores, replays all WAL
docker compose -f deploy/compose.yaml exec -u postgres db psql -d shop -Atc "select count(*) from orders"
```

Questions:
1. Read [`scripts/recover-lost-db.sh`](../scripts/recover-lost-db.sh). Why does it pass `--type=default` to the restore container?
   (Hint: what would `docker compose run db` pass to pgBackRest *without* arguments?)
2. What would happen if you simply started the `db` service on an empty volume? Why can that empty database not
   damage the backups? (Search [`docs/troubleshooting.md`](../docs/troubleshooting.md) for "system-id".)
3. Is the order count after recovery lower, equal or higher than before? Why can it be higher?

<details><summary>Answers</summary>

1. Without arguments, Compose passes the service's `command:` (`postgres -c …`) to pgBackRest, which fails with
   "option '-c' must begin with --". Any explicit option replaces that command; `--type=default` means "replay
   every archived change".
2. The PostgreSQL image would create a brand-new, empty database. Its system identifier differs from the one the
   repository was created for, so `archive-push` is refused ("system-id … do not match") and nothing is written
   over the real backups.
3. Equal or higher: the script archives the latest WAL first, and the application keeps inserting orders between
   your count and the moment it is stopped.

</details>

## Lab 10: The whole proof

```bash
scripts/e2e.sh          # deletes this stack's data, then runs all 11 sections
cat reports/e2e-results.md
```

Compare each measured number with [`docs/test-results.md`](../docs/test-results.md). Clean up with `scripts/down.sh --purge`.

Next: [Glossary](glossary.md)
