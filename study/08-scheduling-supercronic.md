# 8. Scheduling with supercronic

## What is it?

**cron** runs commands on a timetable written as five fields: minute, hour, day of month, month, day of week. **supercronic** is a cron implementation made for containers: it reads a normal crontab file, runs jobs in the foreground, writes their output to the container log, and needs no root privileges.

## Why this project uses it

Backups, verification, drills and metrics must run on a schedule on the backup host. Classic `cron` inside a container is awkward: it wants to run as root, daemonizes, mails output instead of logging it, and loses environment variables. supercronic fixes all of that, and it is a single static binary.

**Alternatives:** systemd timers (on a VM), Kubernetes CronJobs (one pod per run), a CI scheduler (GitHub Actions `schedule`), an external job scheduler.

## How it works

```
┌──── minute (0-59)
│ ┌── hour (0-23)
│ │ ┌ day of month
│ │ │ ┌ month
│ │ │ │ ┌ day of week (0 = Sunday)
30 * * * *   run-backup incr      → at minute 30 of every hour
0 1 * * 0    run-backup full      → Sundays at 01:00
0 1 * * 1-6  run-backup diff      → Monday to Saturday at 01:00
```

All times are **UTC** (containers run in UTC). Each job is a small script that does one thing and reports its result to the Pushgateway, so a job that fails is visible on the dashboard and can alert.

## Where it is integrated

The binary is downloaded in [`image/Dockerfile`](../image/Dockerfile), and its SHA-256 is checked before it is used:

```dockerfile
RUN curl -fsSL -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
 && echo "${SUPERCRONIC_SHA256}  /usr/local/bin/supercronic" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/supercronic
```

The timetable is [`image/crontab`](../image/crontab):

```
0 1 * * 0     run-backup full
0 1 * * 1-6   run-backup diff
30 * * * *    run-backup incr
0 3 * * *     run-verify
0 4 * * *     restore-drill
* * * * *     backup-metrics
```

The backup host starts it (as the `postgres` user) after the stanza is ready, in [`image/bin/entrypoint`](../image/bin/entrypoint):

```bash
gosu postgres bash -c 'init-stanza && exec supercronic -passthrough-logs /etc/backup.crontab' &
```

The order of the night matters: the differential at 01:00, verification at 03:00 (checks it), the drill at 04:00 (restores it).

## Try it

```bash
docker compose -f deploy/compose.yaml logs backup | grep -E 'job (succeeded|failed)' | tail
docker compose -f deploy/compose.yaml exec backup cat /etc/backup.crontab

# run any job by hand, exactly as the scheduler would
docker compose -f deploy/compose.yaml exec backup run-backup incr
docker compose -f deploy/compose.yaml exec backup backup-metrics
```

## Common mistakes

- **Forgetting the time zone.** "01:00" in a container is 01:00 UTC.
- **Jobs that fail silently.** A cron job's exit code is invisible unless something records it. Here every job publishes success or failure.
- **Overlapping jobs.** Two backups at once fail (pgBackRest takes a lock). Space the schedule, as done here.
- **Downloading binaries without checking them.** Pin the version and verify the checksum.

## Check yourself

1. When does `0 1 * * 1-6` run?
2. Why is the verification scheduled before the drill?
3. Why does every job push its result instead of relying on the scheduler's log?

<details><summary>Answers</summary>

1. At 01:00 UTC from Monday to Saturday.
2. Verification reads the repository first, including the fresh differential; then the drill restores it. A verify failure explains a later drill failure.
3. Logs are not watched by anyone; metrics are. Pushing the result lets Prometheus alert when a job fails or stops running.

</details>

Next: [Monitoring](09-monitoring.md)
