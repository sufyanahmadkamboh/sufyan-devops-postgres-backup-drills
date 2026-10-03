# 4. pgBackRest

## What is it?

**pgBackRest** is an open-source backup and restore tool made for PostgreSQL. It takes full, differential and incremental backups, archives WAL, restores (also to a point in time), verifies checksums, compresses, encrypts, and stores everything on local disks or object storage (S3, Azure, GCS).

## Why this project uses it

It is the most complete free tool for production PostgreSQL backups: parallel, resumable, block-incremental, with built-in encryption and a `verify` command. One tool covers backups, WAL archiving and restores, so there is one configuration and one repository to reason about.

**Alternatives:** **WAL-G** (similar idea, popular on Kubernetes), **Barman** (EDB's tool, server-based), `pg_basebackup` + a custom WAL archive script (built into PostgreSQL, but you write retention, encryption and verification yourself), managed services (RDS snapshots).

## How it works

### Stanza
A **stanza** is pgBackRest's name for "one PostgreSQL cluster and its backups". This project's stanza is `main`. `stanza-create` prepares the repository; `check` proves that WAL archiving reaches it.

### Repository
The **repository** (`repo1`) is where backups and WAL go. Here it is an S3 bucket (`repo1-type=s3`), encrypted (`repo1-cipher-type=aes-256-cbc`) and compressed with zstd.

### Database host and backup host
Production setups often run pgBackRest on a **dedicated backup host** (also called repository host):

| | Database host (`db`) | Backup host (`backup`) |
|---|---|---|
| runs | PostgreSQL + `pgbackrest server` | `pgbackrest server` + the scheduler |
| knows the S3 key and the encryption passphrase | **no** | yes |
| can reach object storage | **no** | yes |
| sends WAL with | `archive-push` → backup host | stores it in S3 |
| takes backups | no | yes, reading the database's files through the db host's server |

So if the database server is compromised, the attacker finds no storage credentials and cannot delete the backups.

### TLS server and mutual TLS
The two hosts talk through pgBackRest's built-in **TLS server**. Both sides present certificates signed by the project's private CA (**mutual TLS**). `tls-server-auth=db=main` on the backup host means: "a client whose certificate says `CN=db` may use stanza `main`". Nothing else gets in.

### Asynchronous archiving
With `archive-async=y`, `archive-push` returns quickly and a background process sends WAL in batches from a local **spool** directory. If the backup host or the storage is down, WAL waits in the queue (up to `archive-push-queue-max`) and is sent once it is back.

### Restore options used here
- `--delta`: compare checksums and copy only files that differ (fast when the data directory is mostly intact).
- `--type=time --target=...`: point-in-time recovery.
- `--archive-mode=off`: the restored copy must **not** archive WAL into the real repository (important for drills).
- `--recovery-option="restore_command=..."`: how the restored database fetches WAL (`archive-get`).

### verify
`pgbackrest verify` reads every backup file and WAL segment in the repository and checks it against the checksum stored when it was written. It finds damaged or missing files long before you need them.

## Where it is integrated

The configuration is generated at container start by [`image/bin/entrypoint`](../image/bin/entrypoint), from environment variables and Docker secrets. The database host (`render_db`):

```ini
[global]
repo1-host=${BACKUP_HOST:-backup}
repo1-host-type=tls
repo1-host-cert-file=${CERTS}/db.crt
archive-async=y
compress-type=zst
archive-push-queue-max=${ARCHIVE_QUEUE_MAX:-4GiB}
tls-server-auth=${BACKUP_HOST:-backup}=${STANZA}

[${STANZA}]
pg1-path=${PG_PATH}
```

The backup host (`render_backup`) holds the repository options, including the secrets:

```ini
repo1-type=s3
repo1-s3-bucket=${S3_BUCKET:-pgbackrest}
repo1-s3-endpoint=${S3_ENDPOINT:-s3}
repo1-storage-ca-file=${CERTS}/ca.crt
repo1-s3-key=$(cat /run/secrets/s3_access_key)
repo1-cipher-type=aes-256-cbc
repo1-cipher-pass=$(cat /run/secrets/repo_cipher_pass)
...
[${STANZA}]
pg1-host=${DB_HOST:-db}
pg1-host-type=tls
```

The files end up mode `0640`, owned by `postgres`. On the first start, [`image/bin/init-stanza`](../image/bin/init-stanza) creates the stanza, proves archiving works and takes the first full backup:

```bash
pgbackrest --stanza="$STANZA" check
log "WAL archiving works"
...
  log "repository is empty: taking the first full backup"
  run-backup full
```

Restores of the live database use the `restore` role of the same image (`ROLE=restore`), started by [`scripts/pitr.sh`](../scripts/pitr.sh):

```bash
exec gosu postgres pgbackrest --stanza="$STANZA" --delta --log-level-console=info restore "$@"
```

## Try it

```bash
# what is in the repository
docker compose -f deploy/compose.yaml exec -u postgres backup pgbackrest --stanza=main info

# prove archiving works end to end (switches WAL and waits for it to arrive)
docker compose -f deploy/compose.yaml exec -u postgres backup pgbackrest --stanza=main check

# check every file in the repository against its checksum
scripts/verify.sh

# the generated configuration (note: the db host has no S3 key and no passphrase)
docker compose -f deploy/compose.yaml exec db cat /etc/pgbackrest/pgbackrest.conf
```

## Common mistakes

- **Losing the encryption passphrase.** Without it, the backups are random bytes. Store it in a password manager or a secrets vault, outside the servers (lab 6 shows what happens).
- **Letting the restored copy archive WAL.** A test restore that archives into the same stanza can corrupt the real history. Use `--archive-mode=off`.
- **Restoring while PostgreSQL still runs.** pgBackRest refuses (`unable to restore while PostgreSQL is running`), and rightly so. Stop the database first; make sure it shut down cleanly.
- **Never running `verify`.** Damaged files are found only when you need them.

## Check yourself

1. Why does the database host not have the S3 key?
2. What does `tls-server-auth=db=main` allow?
3. What problem does `archive-async=y` solve when storage is down?

<details><summary>Answers</summary>

1. If the database server is compromised, the attacker cannot use the key to read, change or delete the backups. Only the backup host can reach storage.
2. Clients presenting a certificate (signed by the project CA) with the name `db` may use the stanza `main` on this TLS server. Every other client is refused.
3. WAL is queued locally in the spool directory and `archive_command` keeps succeeding quickly, so the database keeps running. Once storage is back, the queue is sent.

</details>

Next: [Object storage (S3)](05-object-storage-s3.md)
