# Runbook

All commands run from the repository root. `pgbackrest` commands run as `postgres` on the backup host:
`docker compose -f deploy/compose.yaml exec -u postgres backup pgbackrest --stanza=main <command>`.

## Daily check (2 minutes)

1. Grafana → *PostgreSQL backups & restore drills*: the first row must show **PASSED, PASSED, 0 missing**.
2. *Age of newest backup*: incr under 2 h, full under 8 days.
3. *Firing alerts*: 0.

## Alerts

| Alert | Meaning | Do this |
|---|---|---|
| WalArchivingFailing | new changes are not reaching the backups | `docker compose logs backup s3`; check the backup host and the object store; watch DB disk (spool grows) |
| WalArchivingStale | nothing archived for 10 min | same as above; is the database up? |
| BackupFailed | the last backup of a type failed | `docker compose logs backup`; run it again: `scripts/backup.sh <type>` |
| BackupTooOld / FullBackupTooOld | the schedule is not running | `docker compose ps backup`; supercronic logs; take a backup by hand |
| RepositoryUnreadable | pgBackRest cannot read the repository | `pgbackrest info`; S3 reachable? credentials/passphrase changed? |
| BackupVerifyFailed | files in S3 no longer match their checksums | `scripts/verify.sh` output lists them; take a new full backup; investigate the storage |
| RestoreDrillFailed | the latest backup could not be restored or failed a check | `docker compose logs backup`, `/var/log/pgbackrest/drill-postgres.log`; treat as an incident |
| RestoreDrillMissing | no drill in 26 h | supercronic running? run `scripts/drill.sh` |
| RestoreTooSlow | measured RTO over 30 min | more frequent full backups, raise `PROCESS_MAX` |
| RestoreDataLossHigh | the copy was > 5 min behind | archiving slow or failing; see WalArchiving* |

## Point-in-time recovery (accidental DELETE / DROP / bad migration)

1. Find the time *just before* the mistake (application logs, `pg_stat_statements`, the person who did it). Use UTC.
2. `scripts/pitr.sh "2026-10-03 14:04:59+00"` and type `restore` to confirm. The script:
   - archives the latest WAL
   - stops the app and the database
   - restores (delta)
   - starts the database on a new timeline, then restarts the app
3. Check the data, then take a fresh full backup: `scripts/backup.sh full`.

Everything after the target time is gone. To keep later changes, restore into a separate copy instead (as the drill does) and copy the needed rows back.

## Database data lost (disk failure, deleted volume, new server)

`scripts/recover-lost-db.sh` (type `recover` to confirm). It:
1. stops the application and the database
2. deletes the damaged volume
3. restores the latest backup and replays every archived WAL file (`--type=default`)
4. starts the database and the application

Measured: 16 s, with every archived order back.

On a **new server**:
1. Check out this repository and copy `.secrets/` from your secure storage (S3 keys, passphrase, certificates).
2. Point `S3_ENDPOINT` at the real bucket, then run `scripts/up.sh`.
3. Run `scripts/recover-lost-db.sh --yes` immediately.

The empty database that `up.sh` creates cannot damage the repository: pgBackRest refuses its WAL with
"system-id do not match" (observed in testing).

Never start the `db` service on an empty volume and walk away. PostgreSQL then creates a new, empty
database, and its WAL is rejected by the repository.

## Secrets

- Passphrase (`.secrets/repo_cipher_pass`): **store a copy outside the server** (password manager / vault). Without it the backups are unreadable — tested in the e2e (*Lost encryption key*).
- Rotating S3 keys: update `.secrets/s3_*` and the S3 identities, `docker compose up -d backup s3`.
- Certificates expire after 825 days: delete `.secrets/certs/*.crt` and re-run `scripts/setup.sh`, then restart db and backup.

## Moving to AWS S3

Set on the `backup` service: `S3_ENDPOINT=s3.<region>.amazonaws.com`, `S3_PORT=443`, `S3_URI_STYLE=host`, `S3_REGION=<region>`, `S3_BUCKET=<bucket>`; the CA file can stay (it is only used for the private CA). Create the stanza (`init-stanza` runs on start). Enable bucket versioning or Object Lock.

## Upgrades

- pgBackRest: change `PGBACKREST_VERSION` in `image/Dockerfile` (db and backup must run the same version), rebuild, run `scripts/e2e.sh`.
- PostgreSQL major version: new stanza version (`pgbackrest stanza-upgrade` after `pg_upgrade`), then a new full backup.
