# 0. The big picture

## The problem, without jargon

Imagine you keep a **spare key** to your house at a friend's place. You feel safe. Then one day you lock yourself out, go to your friend, and discover the key doesn't fit: the lock was changed two years ago. The spare key existed, but it was **never tested**.

Database backups often fail in exactly this way:

- The backup job ran every night and said "success", but the files cannot be restored.
- The backup is fine, but nobody knows the restore takes 9 hours.
- The backup is from last night, and the mistake happened at 4 pm, so a whole day of orders is gone.
- The backups are encrypted, and the only copy of the key was on the server that just died.
- The backups were stored next to the database, and the same attacker deleted both.

## The idea of this project

Treat backups like a **fire drill**: practise the emergency regularly, so that on the real day everyone knows it works and how long it takes.

| Everyday picture | In this project |
|---|---|
| A diary in which the shop writes down every sale, line by line | PostgreSQL's **WAL** (write-ahead log) |
| Photocopying the whole diary once a week | A **full backup** |
| Copying only the pages that changed since the last copy | **Differential** and **incremental** backups |
| Sending each finished diary page to a safe deposit box immediately | **WAL archiving** to object storage (S3) |
| A safe deposit box in another building, which only one trusted person can open | A **separate backup host** with the only storage key, and storage the database cannot even reach |
| The box is locked and the contents are in code | **Encryption** of every backup file |
| Every night someone rebuilds the shop's records from the box and checks nothing is missing | The nightly **restore drill** |
| "Put the records back exactly as they were at 15:59, just before the mistake" | **Point-in-time recovery** (PITR) |
| A noticeboard showing when the last drill passed | **Prometheus** alerts and a **Grafana** dashboard |

## What the system does, in one breath

A small shop application writes orders into **PostgreSQL**. Every change is recorded in the WAL. The WAL is sent at least every minute, through a dedicated **backup host**, into **encrypted object storage**. The backup host also takes full, differential and incremental backups on a schedule. Every night it **restores the latest backup into a scratch copy**, checks that no order is missing and nothing is corrupted, measures how long it took, and reports the result. If anything goes wrong (archiving stops, a backup fails, a file in storage is damaged, a drill fails), an **alert** fires.

```
 app ──orders──► db (PostgreSQL) ──WAL──► backup host ──encrypted──► object storage (S3)
                                              │  ▲
                         nightly: restore ────┘  └── backups: weekly full, daily diff, hourly incr
                         into a scratch copy, check, report
                                              │
                               Pushgateway ──► Prometheus ──► alerts + Grafana dashboard
```

## Two numbers that matter

- **RPO (recovery point objective):** how much recent data you can afford to lose. Here: changes are archived at least every 60 seconds, so in a disaster you lose at most about a minute.
- **RTO (recovery time objective):** how long you can afford to be down while restoring. The drill **measures** this every night instead of guessing.

## Where to go next

Chapter 1 explains the database itself. If you already know PostgreSQL, skim it and go to chapter 2, where the real magic (the WAL) is.

Next: [PostgreSQL basics](01-postgresql-basics.md)
