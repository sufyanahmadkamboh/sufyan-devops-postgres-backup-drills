# Troubleshooting

Problems found while building and testing this project.

**`ERROR: [031]: option '-c' must begin with --` when running the restore role**
`docker compose run db` without arguments passes the service's `command:` (`postgres -c …`) to pgBackRest.
Always give restore options explicitly; `scripts/recover-lost-db.sh` uses `--type=default`.

**An empty database started after a failed restore**
If the restore fails and the `db` service is started anyway, the PostgreSQL image initialises a new, empty
database. pgBackRest refuses its WAL (`ArchiveMismatchError … system-id … do not match`), so the repository is
not damaged — stop it, delete the volume, and run `scripts/recover-lost-db.sh` again.

**Trivy: 1 CRITICAL + 21 HIGH in `/usr/local/bin/gosu`**
The official postgres image ships `gosu`, built with an old Go runtime. The image now deletes it and installs
a 5-line shim with the same interface that uses util-linux `setpriv` (`image/bin/gosu`). Overwriting the file
was not enough: the old binary stayed in a lower image layer and Trivy still reported it, so it is deleted
explicitly with `RUN rm` first.

**MinIO image not available / outdated**
MinIO stopped publishing images in October 2025 and the project was archived in 2026. The lab uses SeaweedFS
4.48 (`weed server -s3` with HTTPS). Any S3-compatible storage or AWS S3 works with pgBackRest.

**`s3` unhealthy in CI (Linux) but fine on Windows**
SeaweedFS starts as root and then switches to the `seaweed` user. The first `setup.sh` made `.secrets/` mode
0700, so that user could not reach its certificate; Windows does not enforce these modes, so it only failed on
Linux. `.secrets/` is now 0711 (files can be opened, the directory cannot be listed) and only `ca.key` stays 0600.

**`s3` container "unhealthy" on first start**
The first start creates SeaweedFS volumes and takes 1–3 minutes. The healthcheck uses `curl` with the private CA
(busybox `wget` resolved `localhost` to IPv6, where nothing listened) and has a 180 s `start_period`.

**`s3-init` fails with "bucket pgbackrest already exists"**
Bucket creation must be idempotent: the init now lists buckets first.

**`ERROR: [038]: unable to restore while PostgreSQL is running`**
The database had been stopped uncleanly (a `postmaster.pid` was left). Cause: SIGTERM = PostgreSQL *smart*
shutdown, which waits for clients; Docker killed it after 10 s. Fix: `stop_signal: SIGINT` (fast shutdown) and the
entrypoint forwards SIGINT; a stop now takes about 1 s and is clean.

**`unable to load cert file '/etc/pgbackrest/tls/db.crt'` during PITR**
The `restore` role looked for certificates named after the role (`restore.crt`). It now presents the database's
certificate (`CERT_NAME=db`), which is the identity the backup host authorises (`tls-server-auth=db=main`).

**`verify` seemed to hang after damaging a backup file**
The test first replaced a 2.5 MB bundle with a 4 KB file. pgBackRest kept retrying reads beyond the end of the
object. Real bit rot keeps the size, so the test now overwrites 4 KiB inside the file; `verify` then reports
`checksum invalid: 1` within seconds and the drill fails with `zst error: Data corruption detected`.

**`verify` reported failure on a healthy repository (first version)**
The script searched the output for "checksum invalid", which also matches `checksum invalid: 0`. It now requires
`status: ok` and fails only on non-zero counters.

**WAL file names end in `.gz` although `compress-type=zst`**
`archive-push` runs on the database host and uses that host's settings; `compress-type=zst` is now set there too.

**`archive_command` failures right after `scripts/up.sh`**
WAL archiving starts before the backup host is up, so the first few `archive-push` calls fail and
`pg_stat_archiver.failed_count` starts above 0. The alert uses `increase(...[5m])`, so old failures do not fire it
(covered by a promtool test).

**Alert rule bugs found by promtool tests**
- `RestoreTooSlow` showed "1s": `success == 1 and duration > 1800` returns the left side's value. The measured
  value now comes first.
- `WalArchivingFailing` printed fractional failures (`increase()` extrapolates); rounded in the summary.
- A "stale" test with sparse samples never fired: samples older than 5 minutes are stale in Prometheus.

**`BackupFailed` firing after a storage outage**
Correct behaviour: the hourly incremental backup that ran during the outage failed. The next successful backup of
that type clears it (the e2e test now takes one after the outage).

**Restore drill passes but data loss is ~1 minute**
Expected: changes are archived at least every 60 s (`archive_timeout`). Lower it for a smaller RPO at the cost of
more WAL files.

**Windows / Git Bash**
- `openssl` from Git for Windows needs `C:/...` paths when `MSYS_NO_PATHCONV=1` is set: `scripts/setup.sh` uses
  `pwd -W`.
- `tr ... < /dev/urandom | head` exits with SIGPIPE under `pipefail`: secrets come from `openssl rand` instead.
- `os.geteuid` does not exist on Windows: the metrics exporter checks for it before use (unit tests run on Windows).
