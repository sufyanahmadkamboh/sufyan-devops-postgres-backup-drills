# Glossary

| Term | Meaning |
|---|---|
| **amcheck / pg_amcheck** | PostgreSQL extension and tool that check tables and indexes for corruption |
| **archive_command** | the command PostgreSQL runs for every finished WAL segment; here `pgbackrest archive-push %p` |
| **archive_timeout** | forces a WAL segment switch after N seconds with changes; bounds data loss (RPO) |
| **archive-async** | pgBackRest mode that queues WAL locally and sends it in the background |
| **backup host (repository host)** | the separate server that runs backups and holds the repository credentials |
| **bit rot** | silent damage to stored data over time; found by checksums (`verify`) |
| **block incremental** | storing only changed blocks of a file, not the whole file (`repo1-block`) |
| **bucket** | a top-level container in object storage |
| **bundle** | many small files packed into one object (`repo1-bundle`) |
| **CA (certificate authority)** | the key that signs certificates; everyone trusting the CA trusts its certificates |
| **commit** | the moment a transaction becomes permanent |
| **cron / crontab** | time-based job scheduling and its file format |
| **data directory (PGDATA)** | the folder holding all of a PostgreSQL server's data |
| **delta restore** | restore that copies only files that differ from the backup |
| **differential backup** | files changed since the last full backup |
| **Docker secret** | a file mounted into a container at `/run/secrets/<name>` |
| **drill (restore drill)** | a regular, automated test restore with checks |
| **expire** | pgBackRest removing backups (and WAL) beyond the retention |
| **full backup** | a copy of every database file |
| **incremental backup** | files changed since the last backup of any type |
| **mutual TLS (mTLS)** | both sides of a connection prove their identity with certificates |
| **object storage / S3** | storage of files (objects) in buckets over an HTTP API |
| **Object Lock** | S3 feature that prevents deleting or changing objects for a period |
| **PITR (point-in-time recovery)** | restoring a database to an exact moment using a backup plus WAL |
| **promotion** | a recovered database leaving recovery and becoming read-write |
| **Pushgateway** | receives metrics pushed by batch jobs, for Prometheus to scrape |
| **pg_stat_archiver** | PostgreSQL view counting archived and failed WAL segments |
| **recovery** | PostgreSQL replaying WAL to bring a copy up to date |
| **recovery target** | where recovery stops: end of WAL, a time, a transaction, a name |
| **repository (repo1)** | where pgBackRest stores backups and WAL |
| **retention** | how many backups are kept (`repo1-retention-full`) |
| **role** | a PostgreSQL user or group |
| **RPO (recovery point objective)** | the maximum acceptable data loss, measured in time |
| **RTO (recovery time objective)** | the maximum acceptable time to restore service |
| **SeaweedFS** | open-source distributed storage with an S3-compatible API; the lab's object store |
| **segment (WAL segment)** | one 16 MiB WAL file |
| **spool** | local queue directory for asynchronous WAL archiving |
| **stanza** | pgBackRest's name for one PostgreSQL cluster and its backups (`main`) |
| **supercronic** | a cron for containers |
| **timeline** | a branch in a database's history, created by point-in-time recovery |
| **TLS server (pgBackRest)** | pgBackRest's built-in service that lets hosts talk securely |
| **verify** | pgBackRest command that checks every repository file against its checksum |
| **WAL (write-ahead log)** | the log of every change, written before the data files are changed |

Next: [Interview questions](interview-questions.md)
