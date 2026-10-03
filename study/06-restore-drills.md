# 6. Restore drills

## What is it?

A **restore drill** is a planned, regular restore of your backups into a separate place, followed by checks that the result is complete and correct. It answers the only question that matters about backups: *can we get the data back, and how long does it take?*

## Why this project uses it

"The backup job succeeded" only proves that some files were written. Real restores fail for many reasons nobody notices in daily operation: a damaged file in storage, a missing WAL segment, a changed encryption key, a version mismatch, a restore that takes ten times longer than expected. This project restores **every night**, automatically, and alerts when a drill fails or does not run. Untested backups are a guess; tested backups are a fact.

**Alternatives:** manual restore tests a few times a year (better than nothing, but rare and easily skipped), restoring into a staging environment as part of another job, managed "backup testing" services.

## How it works: RTO and RPO

- **RTO (recovery time objective):** how long a restore may take. The drill measures the real time: download + start + WAL replay + checks. The alert `RestoreTooSlow` fires above 30 minutes.
- **RPO (recovery point objective):** how much data may be lost. The drill measures it directly: the newest order in the live database minus the newest order in the restored copy. The alert `RestoreDataLossHigh` fires above 5 minutes.

## How the drill works, step by step

[`image/bin/restore-drill`](../image/bin/restore-drill) describes itself at the top:

```bash
#  1. Note the newest order in the live database (the point we should be able to get back to).
#  2. Restore the latest backup + all archived WAL from S3 into a scratch directory on this host.
#  3. Start that copy as a separate PostgreSQL (port 5433, no network, no WAL archiving).
#  4. Check it: no missing orders, how much recent data was not yet archived, no corruption (amcheck).
#  5. Throw the copy away and publish the result for Prometheus and Grafana.
```

**Step 2**, the restore, uses a separate config file (`drill.conf`) whose data path is `/var/lib/drill/data`, so it can never overwrite the real database:

```bash
pgbackrest --config="$CONF" --stanza="$STANZA" --archive-mode=off \
  --recovery-option="restore_command=pgbackrest --config=$CONF --stanza=$STANZA archive-get %f \"%p\"" \
  restore || fail "pgbackrest restore failed"
```

**Step 3** starts the copy without network access and without archiving:

```bash
pg_ctl -D "$DATA" -l /var/log/pgbackrest/drill-postgres.log -w -t 900 \
  -o "-p $PORT -c listen_addresses='' -c unix_socket_directories=/var/run/postgresql -c archive_mode=off -c shared_buffers=128MB" \
  start
```

**Step 4**, the checks:
- **No missing orders:** count the restored orders, then ask the live database (as the read-only `monitor` role) how many orders exist up to the highest restored id. The two numbers must be equal.
- **Data loss:** newest live order time minus newest restored order time.
- **No corruption:** `pg_amcheck --heapallindexed` reads every table and index of the copy and checks their internal structure.

```bash
missing_rows=$(( live_rows_upto - restored_rows ))
data_loss_seconds=$(( live_newest > restored_newest ? live_newest - restored_newest : 0 ))
...
if pg_amcheck -h /var/run/postgresql -p "$PORT" --database="$DB" --heapallindexed --no-dependent-indexes >/tmp/amcheck.log 2>&1; then
  amcheck_ok=1
```

**Step 5** always runs, even when a step fails, because of `trap cleanup EXIT`: the copy is stopped and deleted, and the result (success or failure, plus every number) is pushed to Prometheus.

### What a failed drill tells you
The drill reports *which step* failed (`FAILED at step: restore from repository`). The labs show three real causes it catches: a damaged backup file, a wrong encryption key, and missing WAL.

## Where it is integrated

- The script: [`image/bin/restore-drill`](../image/bin/restore-drill)
- The schedule, nightly at 04:00 UTC: [`image/crontab`](../image/crontab) → `0 4 * * *     restore-drill`
- The drill config: written by `render_backup` in [`image/bin/entrypoint`](../image/bin/entrypoint) (`drill.conf`)
- Manual run: [`scripts/drill.sh`](../scripts/drill.sh)
- Alerts: `RestoreDrillFailed`, `RestoreDrillMissing`, `RestoreTooSlow`, `RestoreDataLossHigh` in [`deploy/prometheus/rules/backups.yml`](../deploy/prometheus/rules/backups.yml)

## Try it

```bash
scripts/drill.sh                 # runs a drill now and prints each step
scripts/status.sh                # repository + the numbers of the last drill
```

Then open Grafana (http://localhost:3000): the top row, "Can we restore right now?", shows the result, the restore time and the data loss.

## Common mistakes

- **Restoring the drill into the production data directory.** Always use a separate path (and here, a separate config file).
- **Letting the drill copy archive WAL.** It would push its own new timeline into the real repository. `--archive-mode=off` prevents it.
- **Only checking that the copy starts.** A copy can start and still miss data. Compare with the source and run `amcheck`.
- **Not alerting on missing drills.** A drill that silently stopped running is as bad as no drill (`RestoreDrillMissing`).

## Check yourself

1. Why does the drill compare "orders up to the highest restored id" instead of "all orders"?
2. What is the difference between RTO and RPO? Which numbers measure them here?
3. Why does the drill use `trap cleanup EXIT`?

<details><summary>Answers</summary>

1. The live database keeps receiving orders during and after the restore; those newer orders cannot be in the copy. Comparing up to the restored point checks for gaps without counting legitimate new orders as missing.
2. RTO is how long recovery takes (`restore_drill_duration_seconds`); RPO is how much recent data is lost (`restore_drill_data_loss_seconds`).
3. So the scratch copy is always stopped and deleted and the result is always published, also when a step fails halfway.

</details>

Next: [The Docker Compose stack](07-docker-compose-stack.md)
