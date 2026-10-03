# 9. Monitoring: Pushgateway, postgres_exporter, alerts and Grafana

## What is it?

- **Prometheus** collects numbers (metrics) over time by *scraping* HTTP endpoints, stores them, and evaluates **alert rules**.
- The **Pushgateway** is a small Prometheus helper for **batch jobs**: a job that runs for a minute and exits cannot be scraped, so it *pushes* its result to the Pushgateway, which Prometheus then scrapes.
- **postgres_exporter** reads PostgreSQL's statistics views and exposes them as metrics.
- **Grafana** shows metrics on dashboards.
- **promtool** is Prometheus's command-line tool; `promtool test rules` runs unit tests for alert rules.

## Why this project uses it

A backup system that nobody watches decays quietly. The monitoring here answers one question: **"if the database died right now, could we get the data back?"** That means watching WAL archiving (continuous), backups (hourly/daily/weekly), the repository's integrity (nightly verify) and the drills (nightly restore).

**Alternatives:** pgBackRest's own `check` in a monitoring system such as Nagios/Icinga, the `pgbackrest_exporter` project, cloud monitoring (CloudWatch), healthchecks.io-style "dead man's switch" pings.

## How it works: where the metrics come from

| Source | Metrics | How |
|---|---|---|
| `run-backup` | `backup_last_run_success{type}`, duration, timestamp | pushed after every backup |
| `run-verify` | `backup_verify_success`, duration, timestamp | pushed after every verification |
| `restore-drill` | `restore_drill_success`, `_duration_seconds` (RTO), `_data_loss_seconds` (RPO), `_missing_rows`, `_amcheck_ok`... | pushed after every drill |
| `backup-metrics` (every minute) | `pgbackrest_backup_last_timestamp_seconds{type}`, sizes, counts, `pgbackrest_stanza_status_code` | reads `pgbackrest info --output=json`, pushes |
| postgres_exporter | `pg_stat_archiver_archived_count`, `pg_stat_archiver_failed_count`, `pg_stat_archiver_last_archive_age` | scraped |

The push helper, [`image/bin/pushmetrics`](../image/bin/pushmetrics), never fails the caller, because a monitoring outage must not stop a backup:

```bash
if ! curl -fsS --max-time 10 --data-binary @- "$url" >/dev/null; then
  echo "pushmetrics: could not push to $url" >&2
fi
exit 0
```

[`image/bin/backup-metrics`](../image/bin/backup-metrics) is a small Python program (standard library only) that turns `pgbackrest info` into metrics. It is unit-tested against **real pgBackRest output** saved in [`tests/fixtures/info-one-full.json`](../tests/fixtures/info-one-full.json) by [`tests/test_backup_metrics.py`](../tests/test_backup_metrics.py).

## How it works: the 11 alert rules

All in [`deploy/prometheus/rules/backups.yml`](../deploy/prometheus/rules/backups.yml):

| Alert | Fires when | Severity |
|---|---|---|
| WalArchivingFailing | archive attempts failed in the last 5 min (for 2 min) | critical |
| WalArchivingStale | nothing archived for more than 10 min | critical |
| BackupFailed | the last backup of a type failed | critical |
| BackupTooOld | no backup of any type for more than 2 h | critical |
| FullBackupTooOld | newest full backup older than 8 days | warning |
| RepositoryUnreadable | pgBackRest reports the stanza is not OK | critical |
| BackupVerifyFailed | verification found damaged or missing files | critical |
| RestoreDrillFailed | the last drill failed | critical |
| RestoreDrillMissing | no drill for 26 h | warning |
| RestoreTooSlow | the drill took more than 30 min (RTO) | warning |
| RestoreDataLossHigh | the restored copy was more than 5 min behind (RPO) | warning |

Two details worth learning from:

```yaml
- alert: WalArchivingFailing
  expr: increase(pg_stat_archiver_failed_count[5m]) > 0
```

`failed_count` only grows. Alerting on `> 0` would fire forever after the very first failure (for example during start-up, before the backup host was ready). `increase(...[5m])` asks "did it fail *recently*?".

```yaml
expr: restore_drill_duration_seconds > 1800 and on(job) restore_drill_success == 1
```

In PromQL, `A and B` returns A's values. Written the other way round, the alert text would say "took 1s" (the value of `success`). The unit tests caught exactly this mistake.

## How it works: testing the alerts

[`tests/prometheus/backups.test.yml`](../tests/prometheus/backups.test.yml) feeds invented time series into the rules and states which alerts must (and must not) fire, and with which text:

```yaml
- interval: 1m
  input_series:
    - series: 'pg_stat_archiver_failed_count{job="postgres"}'
      values: "14x20"
  alert_rule_test:
    - eval_time: 15m
      alertname: WalArchivingFailing
      exp_alerts: []
```

This one proves that old failures do **not** keep the alert firing.

## How it works: the dashboard

[`deploy/grafana/dashboards/backups.json`](../deploy/grafana/dashboards/backups.json), provisioned automatically:
- **Can we restore right now?** last drill PASSED/FAILED, restore time (RTO), data loss (RPO), missing orders, repository check
- **Backups:** age of the newest backup per type, firing alerts, repository size, backups kept
- **Continuous archiving:** seconds since the last archived WAL, archived vs failed per 5 min
- **Drill history:** restore time and data loss per drill, restored orders

## Try it

```bash
# Prometheus UI: http://localhost:9090  →  Alerts tab
# Grafana:       http://localhost:3000  (anonymous viewer)

# what the Pushgateway holds right now
docker compose -f deploy/compose.yaml exec backup curl -s http://pushgateway:9091/metrics | grep -E '^restore_drill|^backup_'

# run the alert rule tests (no stack needed)
docker run --rm -v "$PWD:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules backups.test.yml
```

## Common mistakes

- **Alerting on counters with `> 0`** instead of on their recent increase.
- **No "missing" alerts.** A job that stopped running sends no failure; alert on the *age* of the last success (`BackupTooOld`, `RestoreDrillMissing`).
- **Pushing without grouping labels.** Each backup type is pushed under its own `type` label, so the full backup's result does not overwrite the incremental's.
- **Untested alert rules.** They fail exactly when you need them. promtool tests are cheap.

## Check yourself

1. Why does a backup job push its result instead of being scraped?
2. Why `increase(pg_stat_archiver_failed_count[5m]) > 0` and not `pg_stat_archiver_failed_count > 0`?
3. Which alert catches a drill that silently stopped running?

<details><summary>Answers</summary>

1. It is a batch job: it runs and exits, so there is nothing to scrape afterwards. The Pushgateway keeps its last result for Prometheus.
2. The counter never goes down; a single failure long ago would keep the alert firing forever. The increase over 5 minutes means "failing now".
3. `RestoreDrillMissing`: no drill result newer than 26 hours (or none at all).

</details>

Next: [Security](10-security.md)
