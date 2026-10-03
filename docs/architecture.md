# Architecture

## Data flow

```
app ──INSERT──► PostgreSQL 18 (db) ──WAL segment full or 60 s passed──► archive_command
                                     pgbackrest archive-push (async, local queue in db-spool volume)
                                             │  mutual TLS (client cert CN=db)
                                             ▼
                                   backup host: pgbackrest server ──HTTPS + AES-256──► S3 bucket "pgbackrest"
                                             ▲                                          /main/archive/…  WAL
  supercronic schedule ─► run-backup full|diff|incr ─(TLS to db: copy changed blocks)─► /main/backup/…   backups
                       ─► run-verify      (read every file, check its checksum)
                       ─► restore-drill   (restore into /var/lib/drill, start on :5433, compare, amcheck, delete)
                       ─► backup-metrics  (pgbackrest info → Pushgateway, every minute)
```

Point-in-time recovery (`scripts/pitr.sh`):
1. Force a WAL switch and wait until it is archived.
2. Stop the app and the db.
3. A one-off `restore` container (same image, db volume, db certificate) runs `pgbackrest restore --delta --type=time --target=…`.
4. PostgreSQL replays WAL up to the target, promotes, and starts a new timeline.
5. The db and the app start again.

## Components and why

| Component | Responsibility | Holds secrets |
|---|---|---|
| db | PostgreSQL + pgBackRest TLS server (lets the backup host read data files) | its TLS key only |
| backup | the only host that talks to S3: backups, retention, verify, drills, metrics | S3 keys, encryption passphrase, monitor password, TLS key |
| s3 | object storage (SeaweedFS in the lab) | S3 identities |
| app | writes orders (realistic load + measurable data loss) | app password |
| monitoring | Pushgateway (batch results), postgres_exporter (archiver state), Prometheus (11 rules), Grafana | Grafana admin password |

## Networks

| Network | Members | Purpose |
|---|---|---|
| data | db, app, backup, postgres-exporter | database traffic and pgBackRest TLS |
| storage | s3, s3-init, backup | only the backup host reaches the backups |
| monitoring | prometheus, grafana, pushgateway, postgres-exporter, backup | metrics |

## The restore drill, step by step (`image/bin/restore-drill`)

1. Read the newest order's timestamp from the live database (read-only `monitor` user).
2. `pgbackrest restore` into `/var/lib/drill/data`:
   - with `--archive-mode=off`, so the copy can never push WAL into the real repository
   - with a `restore_command` that uses the drill config
3. Start the copy on port 5433, socket only (`listen_addresses=''`). Wait until WAL replay finishes and it promotes.
4. Compare:
   - **Missing orders:** restored count vs the live count up to the restored maximum id. This must be 0.
   - **Data loss:** live newest minus restored newest (the measured RPO).
5. `pg_amcheck --heapallindexed` on the copy finds corrupted tables and indexes.
6. Stop and delete the copy, then push 8 metrics. Any failure sets `restore_drill_success 0`.

## Decision log

| # | Decision | Why | Trade-off |
|---|---|---|---|
| 1 | pgBackRest (not pg_dump / Barman / WAL-G) | parallel, block-incremental, encrypted, async archiving, delta restore, built-in `verify`, TLS repo host | more concepts than pg_dump |
| 2 | Dedicated backup host (repo host) | credentials and passphrase are not on the database server; a compromised DB cannot delete its backups | one more host; archiving depends on it (queued locally while down) |
| 3 | Mutual TLS (pgBackRest server) instead of SSH | no SSH keys or shells between hosts; certificate CN is the identity | a small private CA to run |
| 4 | Separate `storage` network | enforces #2 at the network level, tested in e2e | — |
| 5 | `archive_timeout=60` | bounds data loss to about a minute even with little traffic | one (mostly empty, compressed) WAL file per minute |
| 6 | `archive-async` with a local spool volume | the database keeps working during storage outages (measured) | WAL piles up on the DB disk; alert after 2 min of failures |
| 7 | Restore drill on the backup host, not a separate VM | self-contained, no Docker socket needed, runs anywhere | needs disk space for one full copy |
| 8 | Pushgateway for job results | the right Prometheus pattern for batch jobs; results survive between runs | last value only, no history of events |
| 9 | SeaweedFS for S3 in the lab | maintained, single container, S3 + HTTPS; MinIO stopped publishing images (2025) and was archived (2026) | lab only; production should use managed S3 |
| 10 | supercronic instead of cron | logs to stdout, works as non-root, clean stop | one binary to pin and verify |
| 11 | Secrets as Docker secrets, copied to postgres-only files | nothing secret in env vars, images or git | `scripts/setup.sh` must run first |
| 12 | Same image for db, backup, app, restore | one build, same pgBackRest version everywhere (required for TLS protocol) | slightly larger app container |
| 13 | SIGINT on stop (`stop_signal`, entrypoint) | PostgreSQL "fast" shutdown is clean and quick; SIGTERM (smart) waited for clients and was killed uncleanly | — |
| 14 | Bit-rot test keeps file size | realistic damage; a truncated object made `verify` retry for minutes (see troubleshooting) | — |
