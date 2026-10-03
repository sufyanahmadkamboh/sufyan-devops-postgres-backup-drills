# 10. Security

## What is it?

Backups contain **all your data**, so they are a prime target: an attacker wants to read them (data theft) or delete them (so ransomware cannot be undone). Backup security means protecting the copies at least as well as the database.

## Why it matters here

Every design decision in this project answers one of three questions:

1. If someone steals a backup file, can they read it? → **encryption at rest**
2. If the database server is hacked, can the attacker destroy the backups? → **separate backup host, network separation, credentials only where needed**
3. Can someone pretend to be the database or the backup host? → **mutual TLS with a private CA**

## How it works

### Encryption at rest
pgBackRest encrypts every file before it leaves the backup host (`repo1-cipher-type=aes-256-cbc` with a long random passphrase). The object store only ever sees encrypted bytes. The end-to-end test downloads a raw backup file and checks that no order data is readable in it.

**The passphrase is the key to everything.** Lose it and the backups are useless (lab 6). Keep a copy in a password manager or secrets vault, **not** only on the backup host.

### Credentials only where they are needed

| Secret | db | backup | app | s3 |
|---|---|---|---|---|
| S3 access key + secret | — | ✔ | — | (identity config) |
| repository passphrase | — | ✔ | — | — |
| `postgres` password | ✔ | — | — | — |
| `app` password | ✔ (to create the role) | — | ✔ | — |
| `monitor` password | ✔ | ✔ (drill comparison) | — | — |

From [`deploy/compose.yaml`](../deploy/compose.yaml):

```yaml
# Dedicated backup host: holds the S3 credentials and the encryption passphrase (the database does not).
backup:
  secrets: [s3_access_key, s3_secret_key, repo_cipher_pass, monitor_password]
```

### Network separation
The `db` and `app` containers are not on the `storage` network (chapter 7). Even with root on the database host, there is no route to the object store.

### Mutual TLS
[`scripts/setup.sh`](../scripts/setup.sh) creates a private CA and one certificate per host (`s3`, `db`, `backup`). The CA's **private key stays in `.secrets/`** and is never mounted into a container:

```bash
C="$ROOT_NATIVE/.secrets/certs"
CA_KEY="$ROOT_NATIVE/.secrets/ca.key"   # kept OUT of certs/, which is mounted into containers
```

Inside each container, the entrypoint copies only that host's certificate and key into a private directory readable by `postgres` alone:

```bash
local name="${CERT_NAME:-$ROLE}"   # the restore role acts as the database host
for f in "$CERTS_SRC"/ca.crt "$CERTS_SRC/$name".crt "$CERTS_SRC/$name".key; do
  [[ -f "$f" ]] && install -o postgres -g postgres -m 0600 "$f" "$CERTS/"
done
```

### Least privilege inside PostgreSQL
Separate roles for the application (`app`) and monitoring (`monitor`, read-only). The drill connects to the live database only as `monitor`.

### Supply chain
- **Pinned versions:** PostgreSQL 18.6, pgBackRest 2.59.2, SeaweedFS 4.48, Prometheus, Grafana and the exporters.
- **Checksums:** supercronic is downloaded with a SHA-256 check.
- **Vulnerability scan:** CI scans the image with Trivy and fails on fixable HIGH/CRITICAL vulnerabilities (chapter 11).

## Where it is integrated

- Secrets and certificates: [`scripts/setup.sh`](../scripts/setup.sh) → `.secrets/` (in [`.gitignore`](../.gitignore))
- Who gets which secret, networks: [`deploy/compose.yaml`](../deploy/compose.yaml)
- TLS settings, private certificate copies: [`image/bin/entrypoint`](../image/bin/entrypoint)
- The checks: section 9 ("Security checks") of [`scripts/e2e.sh`](../scripts/e2e.sh)

## Try it

```bash
# the database host's pgBackRest config has no S3 key and no passphrase (expect 0)
docker compose -f deploy/compose.yaml exec db sh -c 'grep -cE "s3-key|cipher-pass" /etc/pgbackrest/pgbackrest.conf'

# the database cannot resolve the storage host
docker compose -f deploy/compose.yaml exec db getent hosts s3 || echo "no route to storage: good"

# only the files in .secrets/, never in git
git status --ignored | grep .secrets
```

## Common mistakes

- **Backup credentials on the database server.** The first thing ransomware uses.
- **Encryption key stored next to the backups.** Encryption then protects nothing.
- **No copy of the encryption key anywhere else.** One lost server = all backups lost.
- **`verify-tls=n` and self-signed certificates without a CA.** Anyone in between can read or change traffic.
- **The CA private key inside containers.** Whoever reads it can issue themselves a trusted certificate.

## Check yourself

1. Which two protections stop a hacked database server from deleting its backups?
2. Where must a copy of the repository passphrase be kept, and why?
3. Why is the CA private key not in the `certs/` folder?

<details><summary>Answers</summary>

1. The S3 credentials are not on the database host, and the database host is not on the storage network. (In production add bucket versioning/Object Lock.)
2. Outside the servers, for example in a password manager or secrets vault. If the backup host is lost, the passphrase is needed to restore anything.
3. `certs/` is mounted into containers; anyone with the CA key could create certificates that every component trusts.

</details>

Next: [GitHub Actions](11-github-actions.md)
