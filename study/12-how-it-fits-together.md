# 12. How everything fits together

This chapter follows three journeys through the system: one order, one nightly drill, and one accident.

## Journey 1: one order, from insert to the safe deposit box

```
 1  app (loadgen)      INSERT INTO orders ...                         → db, as role app
 2  db (PostgreSQL)    writes the change to the WAL, then commits     → order is crash-safe
 3  db                 segment full or archive_timeout (60 s) reached → calls archive_command
 4  db (pgBackRest)    archive-push %p → queued in /var/spool/pgbackrest (archive-async)
 5  db → backup        sends the segment over mutual TLS (cert CN=db, allowed by tls-server-auth=db=main)
 6  backup             compresses (zstd), encrypts (AES-256), uploads over HTTPS → s3 bucket pgbackrest
 7  db                 pg_stat_archiver.archived_count + 1 → postgres-exporter → Prometheus
```

Files: [`image/bin/loadgen`](../image/bin/loadgen), [`deploy/compose.yaml`](../deploy/compose.yaml) (`archive_command`, `archive_timeout`), [`image/bin/entrypoint`](../image/bin/entrypoint) (both pgBackRest configs).

If step 6 fails (storage down), steps 1-5 keep working: segments wait in the spool, `failed_count` grows, `WalArchivingFailing` fires, and everything is sent once storage is back.

## Journey 2: the nightly drill (04:00 UTC)

```
 1  supercronic        runs restore-drill as postgres on the backup host
 2  restore-drill      asks the live db (role monitor): newest order time
 3  pgbackrest restore latest backup + WAL from s3 → /var/lib/drill/data  (drill.conf, --archive-mode=off)
 4  pg_ctl start       copy on port 5433, no network, replays WAL, promotes
 5  checks             count orders in copy  vs  live orders up to the copy's highest id   → missing = 0?
                       newest live order − newest restored order                          → data loss (RPO)
                       pg_amcheck --heapallindexed                                        → corruption?
 6  cleanup (trap)     stop and delete the copy; push success, RTO, RPO, counts → Pushgateway
 7  Prometheus         restore_drill_success == 0 → RestoreDrillFailed; no drill in 26 h → RestoreDrillMissing
 8  Grafana            "Can we restore right now?" row
```

Files: [`image/crontab`](../image/crontab), [`image/bin/restore-drill`](../image/bin/restore-drill), [`deploy/prometheus/rules/backups.yml`](../deploy/prometheus/rules/backups.yml).

## Journey 3: the accident (`DROP TABLE orders`) and point-in-time recovery

```
 15:00:02  last good moment          (note it: this is the target)
 15:00:05  DROP TABLE orders         (the mistake; the app starts failing)
 scripts/pitr.sh "2026-10-03 15:00:02+00"
   1/4  pg_switch_wal() + pgbackrest check   → the WAL with the last good seconds is now archived
   2/4  docker compose stop app db           → fast shutdown (SIGINT), clean stop
   3/4  ROLE=restore: pgbackrest restore --delta --type=time --target=... --target-action=promote
        delta: only files that differ are copied; WAL is replayed up to 15:00:02 and stops
        before the first commit after it (the DROP)
   4/4  start db → recovery → promotion → new timeline (1 → 2); start app
 then:  take a new full backup; the next drill tests the new timeline
```

Files: [`scripts/pitr.sh`](../scripts/pitr.sh), the `restore` role in [`image/bin/entrypoint`](../image/bin/entrypoint), section 5 of [`scripts/e2e.sh`](../scripts/e2e.sh).

## "Remove X: what breaks?"

| If you remove... | What breaks |
|---|---|
| `archive_timeout=60` | on a quiet database, recent changes may wait hours to be archived; data loss in a disaster grows |
| `archive-async=y` | when storage is down, every `archive_command` call waits and fails; WAL builds up and commits can slow down |
| `--archive-mode=off` in the drill | the scratch copy pushes its own WAL into the real repository and pollutes it |
| the `storage` network separation | the database and app containers can reach the object store (and its unauthenticated admin port) |
| `repo1-cipher-*` | backups are stored in plain text; anyone with bucket access reads all orders |
| the `pgbackrest check` step in `pitr.sh` | the last minute before the mistake is lost |
| `stop_signal: SIGINT` | slow "smart" shutdown can be killed, leaving `postmaster.pid`; the restore then refuses to run |
| `run-verify` | damaged files in storage are discovered only when a restore fails |
| the restore drill | nobody knows whether the backups restore or how long it takes |
| `increase(...[5m])` in `WalArchivingFailing` | one old failure keeps the alert firing forever |
| `pushmetrics` always exiting 0 | a Pushgateway outage would make every backup "fail" |

## Concept → file map

| Concept | File |
|---|---|
| Image, pinned versions | [`image/Dockerfile`](../image/Dockerfile) |
| pgBackRest configuration (db, backup, drill) | [`image/bin/entrypoint`](../image/bin/entrypoint) |
| Stanza creation, first backup | [`image/bin/init-stanza`](../image/bin/init-stanza) |
| Backups and their metrics | [`image/bin/run-backup`](../image/bin/run-backup) |
| Repository verification | [`image/bin/run-verify`](../image/bin/run-verify) |
| Restore drill | [`image/bin/restore-drill`](../image/bin/restore-drill) |
| Repository metrics | [`image/bin/backup-metrics`](../image/bin/backup-metrics) |
| Schedule | [`image/crontab`](../image/crontab) |
| Database, roles, table | [`image/initdb/10-shop.sh`](../image/initdb/10-shop.sh) |
| Services, networks, secrets | [`deploy/compose.yaml`](../deploy/compose.yaml) |
| Alert rules / their tests | [`deploy/prometheus/rules/backups.yml`](../deploy/prometheus/rules/backups.yml) / [`tests/prometheus/backups.test.yml`](../tests/prometheus/backups.test.yml) |
| Dashboard | [`deploy/grafana/dashboards/backups.json`](../deploy/grafana/dashboards/backups.json) |
| Secrets and certificates | [`scripts/setup.sh`](../scripts/setup.sh) |
| Point-in-time recovery | [`scripts/pitr.sh`](../scripts/pitr.sh) |
| End-to-end proof | [`scripts/e2e.sh`](../scripts/e2e.sh) |
| CI | [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml) |

Next: [Hands-on labs](13-hands-on-labs.md)
