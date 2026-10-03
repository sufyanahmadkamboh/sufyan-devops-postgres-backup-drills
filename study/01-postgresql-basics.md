# 1. PostgreSQL basics

## What is it?

**PostgreSQL** ("Postgres") is an open-source **relational database**: a program that stores data in **tables** (rows and columns) and lets applications read and change it with **SQL**. It is one of the most widely used databases in production, from start-ups to banks.

## Why this project uses it

Backups only matter when the data matters, and the data that matters most in most companies lives in a relational database. PostgreSQL also has the features that make professional backups possible: the write-ahead log, continuous archiving and point-in-time recovery (chapter 2).

**Alternatives:** MySQL/MariaDB (similar ideas: binary log, Percona XtraBackup), managed databases such as Amazon RDS or Cloud SQL (the provider takes the backups, but you still need to test restores), document databases such as MongoDB. The concepts in this guide (full + incremental backups, a log of changes, restore drills) apply to all of them.

## How it works: the five ideas you need

### 1. Server, database, table, row
One **PostgreSQL server** (also called a *cluster* in PostgreSQL language) holds several **databases**. This project has a database called `shop` with one table, `orders`. Each order is a **row**.

### 2. Transactions and commits
A **transaction** is a group of changes that happen all together or not at all. When the application inserts an order, PostgreSQL **commits** it: from that moment the order is guaranteed to survive a crash. That guarantee comes from the WAL (chapter 2).

### 3. Roles (users) and privileges
PostgreSQL controls access with **roles**. This project creates:

| Role | Can do | Used by |
|---|---|---|
| `postgres` | everything (superuser) | PostgreSQL itself, pgBackRest on the database host |
| `app` | owns `shop`, reads and writes `orders` | the shop application (`loadgen`) |
| `monitor` | read-only, member of `pg_monitor`, `SELECT` on `orders` | postgres_exporter and the restore drill's comparison queries |

Giving every program its **own** role with only the rights it needs is the *least privilege* principle.

### 4. The data directory
Everything PostgreSQL stores lives in one folder on disk, the **data directory** (`PGDATA`). In the official PostgreSQL 18 image it is `/var/lib/postgresql/18/docker`. A physical backup is, in essence, a consistent copy of this folder plus the WAL needed to make it consistent.

### 5. Recovery and promotion
When PostgreSQL starts from a restored backup, it is first in **recovery**: it replays WAL to bring the copy up to date. When it reaches the end (or a target time), it is **promoted**: it becomes a normal read-write database. `select pg_is_in_recovery()` tells you which state it is in.

## Where it is integrated

The database runs from [`image/Dockerfile`](../image/Dockerfile), which starts from the official image and adds pgBackRest:

```dockerfile
FROM postgres:18.6

ARG PGBACKREST_VERSION=2.59.2-1.pgdg13+1
```

On the first start (empty volume), [`image/initdb/10-shop.sh`](../image/initdb/10-shop.sh) creates the roles, the database and the table:

```sql
CREATE ROLE app LOGIN PASSWORD :'app_password';
CREATE ROLE monitor LOGIN PASSWORD :'monitor_password' IN ROLE pg_monitor;
CREATE DATABASE shop OWNER app;
...
CREATE TABLE orders (
  id         bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  customer   text        NOT NULL,
  amount     numeric(10,2) NOT NULL CHECK (amount >= 0)
);
```

The passwords come from Docker **secrets** (files), never from the code. The `created_at` column is important for this project: the restore drill and the point-in-time recovery test use it to know which orders *should* exist after a restore.

The application, [`image/bin/loadgen`](../image/bin/loadgen), inserts an order every half second, like real traffic:

```bash
psql -XAtq -v ON_ERROR_STOP=1 -c \
  "insert into orders (customer, amount) values ('customer-' || (random() * 999)::int, round((random() * 200)::numeric, 2))"
```

## Try it

```bash
# open a SQL prompt on the live database (as the postgres superuser)
docker compose -f deploy/compose.yaml exec -u postgres db psql -d shop

# inside psql:
select count(*), max(created_at) from orders;     -- run it twice: the count grows
\du                                                 -- list roles
select pg_is_in_recovery();                        -- f = normal read-write database
show data_directory;
\q
```

## Common mistakes

- **Copying the data directory with `cp` while PostgreSQL runs.** The copy is inconsistent and may not start. Use a backup tool that coordinates with PostgreSQL (pgBackRest, `pg_basebackup`).
- **Using the superuser for applications.** If the application is hacked, the attacker owns everything. Use separate roles.
- **Thinking a dump (`pg_dump`) is enough for big, busy databases.** A dump is a logical snapshot of one moment: it cannot give you point-in-time recovery, and restoring large dumps is slow.

## Check yourself

1. What is the difference between a database and a table?
2. Why does this project use a separate `monitor` role instead of `postgres` for monitoring?
3. What does "promoted" mean for a restored database?

<details><summary>Answers</summary>

1. A database is a container of tables (and other objects); a table holds rows of one kind of data, for example orders.
2. Least privilege: monitoring only needs to read statistics and the `orders` table, so if its password leaks, nobody can change or delete data.
3. It finished recovery (replaying WAL) and became a normal read-write database. `pg_is_in_recovery()` returns `f`.

</details>

Next: [WAL and point-in-time recovery](02-wal-and-pitr.md)
