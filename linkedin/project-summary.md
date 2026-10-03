# Project summary

**PostgreSQL Backups You Can Trust: Restore Drills & Point-in-Time Recovery** · Intermediate

**What it does:** PostgreSQL 18 with production-grade continuous backups and automatic proof that they restore.
- **Archiving and backups:** pgBackRest archives WAL at least every 60 s through a dedicated backup host into encrypted S3. That host also takes full, differential and incremental backups and verifies every file's checksum.
- **Nightly drill:** a restore drill restores the latest backup into a scratch instance, compares it with the live database (missing rows, measured RPO), runs amcheck, and measures RTO.
- **Monitoring:** every result goes to Prometheus and Grafana, with 11 unit-tested alerts.

**Recovery:**
- `scripts/pitr.sh` restores the live database to any second (delta restore, new timeline).
- `scripts/recover-lost-db.sh` rebuilds a lost database volume from the backups.

**Security:**
- **Isolation:** the database host holds no S3 credentials or passphrase, and sits on a network with no route to storage.
- **Encryption:** mutual TLS with a private CA (CA key kept out of containers), and AES-256 encryption at rest.
- **Supply chain:** pinned, checksum-verified tools; Trivy and hadolint in CI.

**Testing:** the end-to-end suite (11 sections) runs in CI on every push and weekly. It covers:
- backups and drills
- PITR after `DROP TABLE` and a lost database volume
- a storage outage, bit rot and a lost key
- network isolation and encryption at rest
- monitoring

**Measured (lab):**
- Stack up with its first backup in 68 s.
- Drill 6 s with 0 missing orders.
- PITR 10 s with 123/123 orders.
- Lost volume rebuilt in 16 s.
- Storage outage: 0 orders lost.
- Bit rot caught by verify and the drill.

**Stack:** PostgreSQL 18.6, pgBackRest 2.59.2, SeaweedFS 4.48 (S3), Docker Compose, supercronic, Prometheus 3.15, Pushgateway, postgres_exporter, Grafana 13.2, GitHub Actions, Trivy, Python, Bash.
