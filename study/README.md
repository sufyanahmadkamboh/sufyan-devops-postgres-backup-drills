# Study guide: learn every tool used in this project

This guide is for engineers who are **new to DevOps and databases**. You don't need to know any of these tools before you start. Each chapter explains:

1. **What** the tool or idea is, in plain language
2. **Why** this project uses it, and the alternatives
3. **How** it works: the few concepts you really need
4. **Where** it is wired into this repository, with real file paths and snippets
5. **Try it:** commands to run against the running stack
6. **Common mistakes** people make with it
7. **Check yourself:** short questions (answers at the end of each chapter)

> 📄 **Prefer one file?** Download the whole guide as a single PDF: **[study-guide.pdf](study-guide.pdf)** (answers expanded, ready to print).
> Rebuild it after editing with `python study/tools/build_pdf.py`.

## How to use this guide

Read the chapters in order. Each one builds on the previous ones. Do the "Try it" sections with the stack running (`scripts/up.sh`). Reading alone won't make the ideas stick; running the commands will.

| Step | Chapter | You will understand |
|---|---|---|
| 0 | [The big picture](00-big-picture.md) | What the whole project does, in 5 minutes, with no jargon |
| 1 | [PostgreSQL basics](01-postgresql-basics.md) | Databases, tables, transactions, roles and the data directory |
| 2 | [WAL and point-in-time recovery](02-wal-and-pitr.md) | How PostgreSQL records every change, and how that lets you rewind to any second |
| 3 | [Backup types](03-backup-types.md) | Full, differential and incremental backups, retention, and why there are three kinds |
| 4 | [pgBackRest](04-pgbackrest.md) | The backup tool: stanza, repository, backup host, TLS, restore, verify |
| 5 | [Object storage (S3)](05-object-storage-s3.md) | Where the backups live: buckets, keys, HTTPS, SeaweedFS and AWS S3 |
| 6 | [Restore drills](06-restore-drills.md) | Proving every night that the backups really restore: RTO, RPO, amcheck |
| 7 | [The Docker Compose stack](07-docker-compose-stack.md) | The nine services, three networks, secrets and health checks |
| 8 | [Scheduling with supercronic](08-scheduling-supercronic.md) | Running backups, checks and drills on a timetable inside a container |
| 9 | [Monitoring](09-monitoring.md) | Pushgateway, postgres_exporter, the 11 alert rules, their tests and Grafana |
| 10 | [Security](10-security.md) | Encryption at rest, mutual TLS, network separation, where secrets live |
| 11 | [GitHub Actions](11-github-actions.md) | The three CI jobs that test every change |
| 12 | [How everything fits together](12-how-it-fits-together.md) | One order, one nightly drill and one accident, traced through every tool |
| 13 | [Hands-on labs](13-hands-on-labs.md) | Guided exercises, from "look around" to "break the storage" and "break the tests" |
| | [Glossary](glossary.md) | Every term in one place |
| | [Interview questions](interview-questions.md) | 25 questions this project prepares you for, with answers |

## Before you start

**You need:**
- **Docker Desktop** (or Docker Engine on Linux) with Compose v2, running
- **bash** and **openssl**. On Windows, Git Bash has both.
- About **3 GB** of free memory

You do **not** need to install PostgreSQL or pgBackRest: they run inside the project's image, with every version pinned.

```bash
scripts/up.sh    # secrets + certificates, then the database, backup host, storage and monitoring
```

**Time needed:**
- about 1.5 hours to read chapters 0–4
- about 2 hours for chapters 5–12
- 2–3 hours for the labs

The measured results of this project (restore times, data loss, how fast outages are noticed) are in [`docs/test-results.md`](../docs/test-results.md). This guide explains *how* things work; that file shows *what was measured*.

## A tip for learning

Every time you read "this project uses X", open the file mentioned next to it and find the line. The best way to learn a tool is to see it doing a real job, and this repository is that job.
