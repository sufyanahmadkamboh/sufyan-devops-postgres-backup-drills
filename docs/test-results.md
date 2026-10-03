# Test results

All numbers were measured on 2026-10-03:
- **Locally:** Windows 11, Docker Desktop 29.4.3.
- **In CI:** GitHub Actions, `ubuntu-24.04`. See the job summary of each run.

The end-to-end results below come from **one clean run of all 11 sections** (`scripts/e2e.sh`, 898 s, exit 0).

## 1. Static checks

| Check | Result |
|---|---|
| ShellCheck `-S style` (12 scripts + 8 container scripts) | 0 findings |
| yamllint `--strict` | 0 problems |
| ruff | 0 findings |
| pytest (metrics exporter, real `pgbackrest info` JSON fixture) | 7 passed |
| hadolint (Dockerfile, failure threshold: warning) | 0 findings (DL3008 ignored on purpose, documented inline) |
| promtool `check config` / `check rules` | valid / 11 rules |
| promtool `test rules` (6 test groups) | SUCCESS |
| Trivy (HIGH/CRITICAL, fixable) | 0 after replacing the base image's `gosu` (was 1 CRITICAL + 21 HIGH) |

The unit, rule and image tests found 4 real problems (the fourth: the vulnerable `gosu` binary above).
The first three:
- **Precision:** the WAL segment metric lost precision (the timeline was shifted into bits beyond what a float holds exactly).
- **`RestoreTooSlow`:** its summary showed the wrong value. `and` keeps the left-hand value.
- **`WalArchivingFailing`:** it printed fractional failure counts.

## 2. End-to-end (one clean run)

| # | Section | Measured result |
|---|---|---|
| 1 | Fresh start | empty machine → stanza created, WAL archiving checked, first full backup: **68 s** |
| 2 | Normal operation | app writing 20 orders / 10 s; incr 1.3 MB (1.6 s), diff 1.3 MB (1.5 s), incr 64 KB (1.5 s) |
| 3 | Restore drill | **PASSED in 6 s** (restore 4 s); 99 orders, **0 missing**, amcheck clean, newest restored order 1 s behind live |
| 4 | Repository verification | every backup and WAL file valid |
| 5 | `DROP TABLE orders`, then PITR | 123 orders before the target → **123 after recovery**, 0 later rows; back in service in **10 s** on timeline 2; app writing again; new full backup + drill passed |
| 6 | Object storage down | `WalArchivingFailing` after **198 s**; the database kept accepting orders (8 archive failures, WAL queued); archive caught up **35 s** after recovery; alert resolved after 314 s; next incremental backup OK; drill: **0 orders missing** |
| 7 | Bit rot: 4 KiB overwritten inside a backup file (same size) | `verify`: **checksum invalid: 1**; drill **failed** as it should; `BackupVerifyFailed` + `RestoreDrillFailed` fired; original restored → verify and drill pass |
| 8 | Wrong encryption passphrase | nothing restorable (`no backup set found`); `RestoreDrillFailed` fired; right key → drill passes, alert resolved |
| 9 | Database volume deleted | rebuilt from the backups in **16 s**: 1341 orders (1336 archived before the loss; the rest written after); new full backup + drill passed |
| 10 | Security | db and app **cannot resolve** the object store; backup host can (HTTP 200); raw backup files contain **0** readable order strings; db's pgBackRest config has **0** S3 keys/passphrases; S3 without credentials: **403** |
| 11 | Monitoring | Prometheus has drill, verify, backup-age, archiver and stanza series; **no alerts firing** at the end |

## 3. Same test in CI (GitHub Actions run 37093486543, ubuntu-24.04, all 11 sections passed)

| Measure | CI result |
|---|---|
| Empty runner → first full backup | 62 s |
| PITR after `DROP TABLE` | 108/108 orders back, in service in 17 s |
| Storage outage | alert after 188 s, archive caught up 48 s after recovery, 0 orders missing |
| Bit rot | `checksum invalid: 1`, drill failed with `zst error: Data corruption detected` |
| Database volume lost | rebuilt in 20 s |

## 4. Additional measurements during development

These came from earlier runs on the same stack. They're kept because they show variance:

| Measurement | Values seen |
|---|---|
| Stack up with first backup | 48 s, 68 s |
| PITR in service | 7 s (manual), 10 s, 11 s |
| Drill duration | 6 s (every run) |
| Drill data loss (newest restored order behind live) | 1 s to 54 s; bounded by `archive_timeout=60` |
| Outage: alert after / catch-up after recovery | 210 s / 21 s, 198 s / 35 s |
| Lost volume rebuilt | 16 s, 17 s |
| An empty database started by mistake | its WAL was refused by the repository (`system-id … do not match`) |

## 5. Not tested

- **Production-size data:** the lab database is about 30 MB. Restore time grows with size, so the `RestoreTooSlow` alert (30 min) is the guard.
- **Real cloud S3 and multi-region:** the lab uses SeaweedFS. The S3 code path in pgBackRest is the same, and moving to AWS is a configuration change ([runbook](runbook.md)).
- **High availability:** replicas and failover are out of scope.
