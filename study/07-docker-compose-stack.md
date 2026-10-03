# 7. The Docker Compose stack

## What is it?

**Docker** runs programs in **containers**: isolated processes with their own file system, built from an **image**. **Docker Compose** describes several containers, their networks, volumes and secrets in one YAML file and starts them together.

## Why this project uses it

The whole system (database, backup host, storage, application, monitoring) runs on one machine with one command, identical on a laptop, in CI and on a single production VM. Compose also makes the **security design** visible in one file: who can talk to whom, who gets which secret.

**Alternatives:** Kubernetes (for many servers; operators such as CloudNativePG or Crunchy PGO wrap pgBackRest/Barman), plain systemd services on VMs, Ansible-managed hosts.

## How it works: the services

| Service | Image | Job |
|---|---|---|
| `db` | `pg-backup-drills:dev` (`ROLE=db`) | PostgreSQL 18 + pgBackRest TLS server |
| `backup` | same image (`ROLE=backup`) | pgBackRest TLS server, repository access, scheduler |
| `app` | same image (`ROLE=app`) | writes orders continuously |
| `s3` | `chrislusf/seaweedfs:4.48` | S3-compatible object storage (HTTPS) |
| `s3-init` | same | creates the bucket once, then exits |
| `pushgateway` | `prom/pushgateway:v1.11.3` | receives results of backups and drills |
| `postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.20.1` | database metrics, including WAL archiving |
| `prometheus` | `prom/prometheus:v3.15.0` | collects metrics, evaluates alert rules |
| `grafana` | `grafana/grafana:13.2.3` | dashboard |

**One image, several roles.** The `ROLE` variable decides what [`image/bin/entrypoint`](../image/bin/entrypoint) starts. The same pinned PostgreSQL and pgBackRest versions are therefore guaranteed on the database, the backup host and in restores.

## How it works: the three networks

```yaml
# Network separation: the database and the application cannot reach the backup storage at all,
# so a compromised database host cannot read, change or delete its own backups.
networks:
  data:
  storage:
  monitoring:
```

| Network | Members |
|---|---|
| `data` | db, app, backup, postgres-exporter |
| `storage` | s3, s3-init, backup |
| `monitoring` | backup, pushgateway, postgres-exporter, prometheus, grafana |

Only `backup` is on all three. The database can send WAL to the backup host, but it cannot even resolve the name `s3`.

## How it works: secrets, init, health checks

- **Secrets** are files mounted at `/run/secrets/<name>`, never environment variables in the YAML and never in git. They are generated once by [`scripts/setup.sh`](../scripts/setup.sh) into `.secrets/` (ignored by git).
- **`init: true`** runs a tiny init process as PID 1, which forwards signals and reaps child processes. The `db` container runs two processes (PostgreSQL and the pgBackRest server), so this matters.
- **`stop_signal: SIGINT`** on `db`: SIGINT is PostgreSQL's *fast* shutdown. The default SIGTERM means *smart* shutdown (wait for every client to disconnect), which can run past Docker's timeout and leave the database uncleanly stopped, and pgBackRest refuses to restore over a database that looks still running.
- **Health checks** and **`depends_on` conditions** order the start: storage healthy → bucket created → database healthy → backup host starts.

```yaml
backup:
  networks: [data, storage, monitoring]
  ...
  secrets: [s3_access_key, s3_secret_key, repo_cipher_pass, monitor_password]
  depends_on:
    db: {condition: service_healthy}
    s3-init: {condition: service_completed_successfully}
```

## Where it is integrated

- The stack: [`deploy/compose.yaml`](../deploy/compose.yaml)
- The image: [`image/Dockerfile`](../image/Dockerfile) and [`image/bin/`](../image/bin/)
- Start and stop: [`scripts/up.sh`](../scripts/up.sh), [`scripts/down.sh`](../scripts/down.sh) (`--purge` also deletes the data)
- Shared helpers (`compose`, `on_backup`, `sql`, `wait_for`): [`scripts/lib.sh`](../scripts/lib.sh)

## Try it

```bash
scripts/up.sh                                           # first start: builds, starts, waits for the first full backup
docker compose -f deploy/compose.yaml ps                # every service and its health
docker compose -f deploy/compose.yaml logs -f backup    # stanza, backups, scheduler (Ctrl+C to stop following)
docker compose -f deploy/compose.yaml exec db getent hosts s3 || echo "db cannot see s3"
docker compose -f deploy/compose.yaml exec backup getent hosts s3
```

## Common mistakes

- **Putting every container on one network.** Then every container can reach the backups.
- **Passwords as environment variables in the compose file.** They end up in git, in `docker inspect`, in logs. Use secrets.
- **Forgetting `stop_grace_period` and the right stop signal for databases.** A killed database restarts with crash recovery, and some tools refuse to work on it.
- **`docker compose down -v` by accident.** `-v` deletes volumes, which here means the database and the whole backup repository. This project only does it with an explicit `scripts/down.sh --purge`.

## Check yourself

1. Why is the `backup` service the only one on all three networks?
2. What does `init: true` do, and why does the `db` container need it?
3. Why `stop_signal: SIGINT` for PostgreSQL?

<details><summary>Answers</summary>

1. It is the only component that must talk to the database (to back it up), to storage (to write the repository) and to monitoring (to report results). Keeping everything else apart limits what a compromised container can reach.
2. It runs a minimal init as PID 1 that forwards signals and reaps zombie processes. The `db` container runs PostgreSQL and the pgBackRest server side by side.
3. SIGINT triggers PostgreSQL's fast shutdown, which ends sessions and finishes cleanly within seconds; SIGTERM (smart shutdown) may wait too long and get killed.

</details>

Next: [Scheduling with supercronic](08-scheduling-supercronic.md)
