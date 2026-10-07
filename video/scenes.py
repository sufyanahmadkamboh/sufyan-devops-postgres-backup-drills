"""The video: scenes, visuals and narration.

Each scene has a title, a body (HTML from components.py) and steps. A step is one narration segment; elements with
data-s=<n> appear at step n. `hl` highlights code lines (1-based, inclusive) in the scene's code panel. `tts` overrides
the spoken text when the caption spelling would be read badly (the caption always shows `say`).
Every number is from docs/test-results.md (one clean e2e run, 2026-10-03) and the raw logs in reports/.
"""

from __future__ import annotations

from components import arrow, box, card, checklist, code, grid, label, notes, svg, terminal, tile


def S(say: str, hl: tuple[int, int] | None = None, tts: str | None = None) -> dict:
    return {"say": say, "hl": hl, "tts": tts}


REPO = "github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills"

SCENES: list[dict] = []


def scene(chapter: str | None, kicker: str, title: str, body: str, steps: list[dict], layout: str = "full") -> None:
    SCENES.append({"chapter": chapter, "kicker": kicker, "title": title, "body": body, "steps": steps, "layout": layout})


# ---------------------------------------------------------------- 0. Hook
scene("The question", "PostgreSQL backups and restore drills", "You have backups. Do they restore?", svg(
    box(0, 40, 60, 470, 250, "💾", "Nightly backup job", ["\"green\" for months", "nobody reads the logs"], "amber")
    + arrow(0, 515, 185, 640, 185, "bad")
    + box(1, 650, 60, 420, 250, "🔥", "The incident", ["DROP TABLE orders", "at 14:05"], "bad", "#2a1520")
    + arrow(1, 1075, 185, 1200, 185, "bad")
    + box(2, 1210, 60, 470, 250, "😱", "The restore", ["files corrupt, key lost,", "or a day of data gone"], "bad", "#2a1520")
    + box(3, 300, 430, 1120, 150, "🛡️", "This project: prove every day that the backups restore", ["continuous archiving · daily restore drills · alerts · point-in-time recovery"], "ok", "#0f2a22")
    + label(4, 860, 660, "DROP TABLE undone in 10 s · 123 of 123 orders back · bit rot caught before it mattered", 32, "ok", "middle", 900)
), [
    S("Most teams have backups. Far fewer know that their backups actually restore."),
    S("Then one day someone runs drop table orders on the production database, at five past two in the afternoon."),
    S("And during the incident the team finds out that the backup job had been failing for weeks, or the files are corrupt, or the encryption key is gone. Or the newest backup is from last night, so a whole day of orders is lost."),
    S("In this video I will show you a PostgreSQL setup that proves, every single day, that its backups restore. It archives every change within a minute, restores a copy every day and checks it, and alerts when anything is wrong."),
    S("And it is all measured. A dropped table is undone in ten seconds, with all 123 orders from before the accident back, and a silently damaged backup file is caught before anyone needs it. The code and a free study guide are linked in the description."),
])

# ---------------------------------------------------------------- 1. Map
scene(None, "What you will learn", "Backups you can trust, step by step", grid([
    card(0, "⚠️", "The problem", "why backups fail silently", "bad"),
    card(0, "💡", "WAL + point-in-time recovery", "the idea, in plain words", "amber"),
    card(1, "🗺️", "Architecture", "database, backup host, S3, three networks"),
    card(1, "🔐", "Security", "encryption, mutual TLS, no keys on the database"),
    card(2, "🧰", "pgBackRest", "archiving, full, diff, incremental, verify"),
    card(2, "🧪", "The daily restore drill", "restore, start, compare, amcheck"),
    card(2, "📊", "Prometheus + Grafana", "11 alert rules, one dashboard"),
    card(3, "💥", "Disasters, measured", "DROP TABLE, outage, bit rot, lost key, lost disk"),
    card(3, "✅", "Tests in CI", "the whole proof on every push"),
    card(4, "💻", "Run it yourself", "the whole stack on your laptop"),
    card(4, "☁️", "Production on AWS S3", "a configuration change", "ok"),
    card(4, "🧭", "Honest limits", "what this does not cover", "violet"),
], 3, 22), [
    S("Here is the plan. First the problem, and the one idea that makes point in time recovery possible: the write ahead log."),
    S("Then the architecture, with three separate networks, and the security design."),
    S("Then the tools: pgBackRest for backups, the daily restore drill, and the monitoring with Prometheus and Grafana."),
    S("Next, five real disasters, each one measured: a dropped table, a storage outage, bit rot, a lost encryption key, and a lost database disk. And the tests that repeat all of them on every push."),
    S("And finally, how to run the whole stack on your own laptop, and how to move it to AWS S3."),
])

# ---------------------------------------------------------------- 2. Problem
scene("The problem", "Why this matters", "A backup that was never restored is a hope", notes([
    (0, "🤫 Silent failures", "cron jobs fail quietly; nobody reads backup logs until they are needed"),
    (1, "🕑 No point-in-time recovery", "a nightly pg_dump cannot undo a DELETE made at 14:05"),
    (2, "❓ Unknown RTO and RPO", "how long would a restore take, and how much data would we lose?"),
    (3, "🦠 Backups next to the database", "ransomware on the database host takes the backups too"),
    (4, "🧱 Unverified storage", "bit rot is only discovered on the day of the restore"),
]), [
    S("Let us start with the problem. Backup jobs fail silently. A cron job stops working, and nobody reads the backup logs until the day they need them."),
    S("A nightly dump has no point in time recovery. It cannot undo a delete made at five past two. You either lose up to a day of data, or you keep the mistake."),
    S("Ask a team how long a restore would take, and how much data they would lose. Those are the RTO and the RPO, and they usually have no measured answer."),
    S("Often the backups live right next to the database. If an attacker or ransomware gets the database host, the backups go with it."),
    S("And storage is never verified. A damaged file in object storage is only discovered on the day you need it."),
])

# ---------------------------------------------------------------- 3. WAL idea
scene("The idea", "Write-ahead log", "The idea: a full copy plus every change", svg(
    box(0, 40, 70, 380, 200, "📸", "Full backup", ["a copy of the data files", "Sunday 01:00"], "blue")
    + arrow(1, 425, 170, 520, 170)
    + box(1, 530, 70, 1150, 200, "📜", "WAL: the write-ahead log", ["every change, in order, before it touches a table;", "archived to S3 at least every 60 seconds"], "sky")
    + box(2, 40, 340, 1640, 130, "⏪", "Point-in-time recovery", ["restore the full copy, then replay WAL up to any second you choose, for example 14:04:59"], "ok", "#0f2a22")
    + box(3, 40, 520, 790, 150, "⏱️", "RPO", ["data you can lose: at most ~60 s"], "amber")
    + box(3, 890, 520, 790, 150, "🚑", "RTO", ["time to restore: measured every day"], "amber")
), [
    S("Here is the idea. PostgreSQL writes every change into the write ahead log, the WAL, before it changes a table. Start with a full backup: a copy of the data files."),
    S("Then archive every piece of WAL to object storage as it is written. In this project that happens at least every sixty seconds."),
    S("Now you can restore the full copy and replay the WAL up to any second you choose. For example, to four minutes and fifty nine seconds past two, one second before the accident. That is point in time recovery."),
    S("Two numbers describe how good this is. The RPO, how much data you can lose, is bounded by the sixty second archive interval. And the RTO, how long a restore takes, is something this project measures every single day."),
])

# ---------------------------------------------------------------- 4. Architecture
scene("Architecture", "Architecture", "Three hosts, three networks", svg(
    box(0, 30, 40, 420, 190, "🛒", "app", ["a small shop", "writing orders"], "blue")
    + arrow(0, 455, 135, 560, 135)
    + box(0, 570, 40, 470, 190, "🐘", "db", ["PostgreSQL 18", "no S3 keys, no passphrase"], "sky")
    + arrow(1, 1045, 135, 1180, 135, "ok", label="mutual TLS")
    + box(1, 1190, 40, 500, 190, "🗄️", "backup host", ["pgBackRest repository,", "schedule, drills, metrics"], "ok", "#0f2a22")
    + arrow(2, 1440, 225, 1440, 330, "ok", label="HTTPS")
    + box(2, 1190, 340, 500, 170, "🪣", "s3", ["object storage, encrypted", "(SeaweedFS in the lab)"], "violet")
    + box(3, 570, 340, 470, 170, "📈", "Prometheus", ["Pushgateway + exporter", "11 alert rules"], "amber")
    + arrow(3, 1185, 300, 1045, 400, "sky", True)
    + box(3, 30, 340, 420, 170, "📊", "Grafana", ["dashboard as code"], "violet")
    + arrow(3, 565, 425, 455, 425)
    + label(4, 860, 600, "networks:  data (app · db · backup)   storage (backup · s3)   monitoring", 28, "sky", "middle", 800)
    + label(4, 860, 650, "the database and the app cannot even resolve the storage", 28, "bad", "middle", 900)
), [
    S("Here is the architecture. A small shop application writes orders all the time, so that data loss becomes measurable."),
    S("The database is PostgreSQL 18. It archives WAL through a dedicated backup host, over mutual TLS. The database itself holds no storage keys and no encryption passphrase."),
    S("The backup host owns the pgBackRest repository in S3 compatible object storage. In the lab that is SeaweedFS, and in production you swap in AWS S3."),
    S("The backup host also runs the schedule, the verification and the restore drills, and publishes every result to Prometheus. Grafana shows it on one dashboard."),
    S("And there are three separate networks. The database and the application are not on the storage network at all. So even a fully compromised database host cannot read, change or delete its own backups."),
])

scene(None, "Defence in depth", "If the database host is compromised", checklist([
    (0, "1", "Encryption at rest", "AES-256 on every backup and WAL file; the raw files contain no readable orders"),
    (1, "2", "Separation of duties", "S3 credentials and the passphrase live only on the backup host"),
    (2, "3", "Network isolation", "the storage network does not include the database or the app"),
    (3, "4", "Mutual TLS", "database and backup host prove their identity with a private CA"),
]), [
    S("This is defence in depth. First, every backup and WAL file is encrypted at rest with AES 256. The test searches the raw files for order data, and finds none."),
    S("Second, separation of duties. The storage credentials and the encryption passphrase only exist on the backup host, never on the database."),
    S("Third, network isolation, as we just saw."),
    S("And fourth, mutual TLS between the database and the backup host, with certificates from a private certificate authority whose key is kept out of every container."),
])

# ---------------------------------------------------------------- 5. pgBackRest
COMPOSE = """db:
  command:
    - postgres
    - -c
    - wal_level=replica
    - -c
    - archive_mode=on
    - -c
    - archive_command=pgbackrest --stanza=main archive-push %p
    # at least every 60 s, even when traffic is low:
    # this bounds how much recent data a restore can lose
    - -c
    - archive_timeout=60
  networks: [data]"""
scene("The tools", "pgBackRest", "Archiving: every change, within a minute", code("deploy/compose.yaml (excerpt)", COMPOSE, "yaml", 22) + notes([
    (0, "pgBackRest 2.59", "parallel, encrypted, block-incremental"),
    (1, "archive_command", "every WAL segment goes to the repository"),
    (2, "archive_timeout=60", "the RPO bound, even when it is quiet"),
    (3, "networks: [data]", "no route to the storage"),
]), [
    S("The backup tool is pgBackRest, pinned to version 2.59. It does parallel, encrypted and block incremental backups, with asynchronous WAL archiving."),
    S("The database is configured with archive mode on, and an archive command. For every finished WAL segment, PostgreSQL calls pgBackRest, which pushes it through the backup host into the repository.", (6, 9)),
    S("Archive timeout sixty forces a new WAL segment at least every sixty seconds, even when the shop is quiet. That is what bounds the data loss.", (10, 13)),
    S("And notice the networks line: the database is only on the data network.", (14, 14)),
], "code")

CRON = """# Weekly full, daily differential, hourly incremental:
# restore = 1 full + 1 diff + a few incr + WAL.
0 1 * * 0     run-backup full
0 1 * * 1-6   run-backup diff
30 * * * *    run-backup incr
# Read every file in the repository and check its checksum.
0 3 * * *     run-verify
# Restore the latest backup into a scratch copy and check it.
0 4 * * *     restore-drill
# Repository state (backup ages and sizes) for the dashboard.
* * * * *     backup-metrics"""
scene(None, "The schedule", "Full, differential, incremental, verify, drill", code("image/crontab (on the backup host)", CRON, "bash", 23) + notes([
    (0, "Full · diff · incr", "weekly · daily · hourly"),
    (1, "verify", "every file's checksum, daily"),
    (2, "restore-drill", "a real restore, daily"),
    (3, "supercronic", "cron for containers, logs to stdout"),
]), [
    S("The backup host runs a schedule. A full backup every Sunday, a differential every other day, and an incremental every hour. So a restore needs one full, one differential, a few incrementals and the WAL.", (1, 5)),
    S("Every night, verify reads every single file in the repository and checks its checksum. That is how bit rot is found early.", (6, 7)),
    S("Then the restore drill, the heart of the project.", (8, 9)),
    S("Every minute, the repository state is exported for the dashboard. The scheduler is supercronic, a cron built for containers, pinned by its SHA 256 checksum.", (10, 11)),
], "code")

# ---------------------------------------------------------------- 6. Drill
scene("Restore drills", "The daily restore drill", "Prove it restores, every day", checklist([
    (0, "1", "Note the newest live order", "the point we should get back to"),
    (1, "2", "Restore the latest backup + all WAL", "from S3 into a scratch directory on the backup host"),
    (2, "3", "Start the copy", "a separate PostgreSQL on port 5433, no network, no archiving"),
    (3, "4", "Check it", "missing orders, how far behind live, amcheck for corruption"),
    (4, "5", "Throw it away and publish", "RTO, RPO, rows, result → Prometheus"),
]), [
    S("Here is the restore drill. First, it reads the newest order in the live database, with two read only queries. That is the point the copy should get back to."),
    S("Then it restores the latest backup, plus all the archived WAL, from S3 into a scratch directory on the backup host."),
    S("It starts that copy as a completely separate PostgreSQL, on another port, with no network and no WAL archiving, so it can never interfere with production."),
    S("Then it checks the copy: are any orders missing, how far behind the live database is the newest restored order, and does amcheck find any corruption in the tables and indexes?"),
    S("Finally it throws the copy away, and publishes the result: the measured restore time, the measured data loss, the row counts and the verdict."),
])

scene(None, "A real drill", "The drill in the log", terminal([
    (0, "$ scripts/drill.sh", "cmd"),
    (0, "[restore-drill] newest live order: 2026-10-03T03:16:06Z", ""),
    (1, "INFO: repo1: restore backup set 20261003-031517F_20261003-031603I", ""),
    (1, "INFO: restore size = 30.1MB, file total = 1274", ""),
    (1, "INFO: restore command end: completed successfully (3912ms)", "ok"),
    (2, "[restore-drill] files restored in 4 s", ""),
    (2, "[restore-drill] restored 111 orders, missing 0, newest order 1 s older than live", "ok"),
    (3, "[restore-drill] PASSED in 6 s", "ok"),
], "reports/drill-1.log (excerpt)"), [
    S("Here is a real drill from the logs. It notes the newest live order."),
    S("pgBackRest restores the latest backup set, 30 megabytes in 1274 files, in under four seconds."),
    S("The copy has 111 orders, none missing, and its newest order is only one second older than the live database. That one second is the measured data loss."),
    S("The whole drill passed in six seconds. On a production size database this takes longer, and an alert fires if it ever takes more than thirty minutes."),
])

# ---------------------------------------------------------------- 7. Monitoring
scene("Monitoring", "Prometheus + Grafana", "Can we restore right now?",
      '<img class="shot st" data-s="0" src="../../docs/images/grafana-dashboard.png" alt="Grafana dashboard">', [
    S("Every job publishes its result to a Prometheus Pushgateway, and a postgres exporter reports the state of the WAL archiver. The dashboard answers one question first: can we restore right now?"),
    S("At the top: the last drill's result, the measured restore time and data loss, missing orders, and the repository verification. Below: the age of each backup type, firing alerts, the repository size, WAL archiving and the drill history."),
])

scene(None, "Alert rules", "Eleven ways backups can silently stop working", grid([
    card(0, "📜", "WAL archive", "WalArchivingFailing · WalArchivingStale"),
    card(1, "💾", "Backups", "BackupFailed · BackupTooOld · FullBackupTooOld · RepositoryUnreadable"),
    card(2, "🧱", "Integrity", "BackupVerifyFailed"),
    card(3, "🧪", "Drills", "RestoreDrillFailed · RestoreDrillMissing · RestoreTooSlow (> 30 min) · RestoreDataLossHigh (> 5 min)", "amber"),
], 2, 26), [
    S("There are eleven alert rules, one for every way backups can silently stop working. Two watch the WAL archive: failing, or stale."),
    S("Four watch the backups: a failed backup, a backup or full backup that is too old, and a repository that cannot be read."),
    S("One watches integrity: a failed verification."),
    S("And four watch the drills: a failed drill, a missing drill, a restore slower than thirty minutes, and data loss above five minutes. Every rule has a unit test with prom tool."),
])

# ---------------------------------------------------------------- 8. Results
scene("Disasters, measured", "One clean end-to-end run", "Five disasters, each one measured", grid([
    tile(0, "🚀", "Empty machine → first full backup", "68 s", "sky"),
    tile(1, "🗑️", "DROP TABLE → back in service", "10 s", "ok", "123 / 123 orders"),
    tile(2, "🪣", "Storage down ~3.5 min", "0 lost", "ok", "alert after 198 s"),
    tile(3, "🧬", "Bit rot in one backup file", "caught", "ok", "verify + drill + 2 alerts"),
    tile(4, "🔑", "Wrong encryption passphrase", "alert", "amber", "nothing restorable"),
    tile(5, "💽", "Database volume deleted", "16 s", "ok", "rebuilt from S3"),
], 3, 22), [
    S("Now the results, from one clean run of the end to end test. From an empty machine to a running stack with its first full backup took 68 seconds."),
    S("A dropped table was undone in ten seconds, with every order from before the accident back."),
    S("A storage outage of about three and a half minutes lost zero orders."),
    S("A silently damaged backup file was caught by verification and by the drill."),
    S("A wrong encryption passphrase made nothing restorable, and the alert said so."),
    S("And a deleted database volume was rebuilt from the backups in sixteen seconds. Let us look at each one."),
])

scene(None, "Disaster 1", "DROP TABLE orders, then point-in-time recovery", terminal([
    (0, "psql> DROP TABLE orders;          -- 123 orders existed before the accident", "bad"),
    (1, "$ scripts/pitr.sh \"<one second before the DROP>\"", "cmd"),
    (1, "INFO: restore size = 30.1MB, file total = 1274", ""),
    (1, "INFO: restore command end: completed successfully (360ms)", "ok"),
    (2, "==> 4/4 Starting the database", ""),
    (2, " ok Database restored to 2026-10-03 03:16:18.398657+00 in 10 s (new timeline: 2)", "ok"),
    (3, "orders before the target: 123 → after recovery: 123 · rows from after the target: 0", "ok"),
], "reports/pitr.log (excerpt)"), [
    S("Disaster one: someone drops the orders table. At that moment, 123 orders existed."),
    S("One command, pitr dot S-H, with a target time one second before the accident. pgBackRest uses a delta restore, so it only replaces the files that differ, in a third of a second."),
    S("PostgreSQL replays the WAL up to the target, and the database is back in service in ten seconds, on a new timeline, timeline two."),
    S("All 123 orders from before the accident are back, and nothing from after the target. The app starts writing again, and a new full backup and drill pass."),
], "full")

scene(None, "Disaster 2", "The object storage goes down", grid([
    tile(0, "🛒", "Database during the outage", "kept working", "ok", "8 archive failures, WAL queued"),
    tile(1, "🚨", "WalArchivingFailing", "198 s", "amber", "after the outage began"),
    tile(2, "🔄", "Archive caught up", "35 s", "ok", "after storage came back"),
    tile(3, "✅", "Orders lost", "0", "ok", "next drill: 0 missing"),
], 4, 22), [
    S("Disaster two: the object storage goes down for about three and a half minutes. The database keeps accepting orders. WAL archiving fails eight times, and the segments wait in a queue."),
    S("The WAL archiving failing alert fired after 198 seconds."),
    S("When the storage came back, the archive caught up within 35 seconds."),
    S("The next incremental backup worked, and the next drill found zero missing orders."),
])

scene(None, "Disaster 3", "Bit rot: one backup file silently damaged", terminal([
    (0, "# 4 KiB overwritten inside one backup file (same size, so nothing looks wrong)", "dim"),
    (1, "$ scripts/verify.sh", "cmd"),
    (1, "backup: 20261003-031649F, status: invalid, total files checked: 1275, total valid files: 1274", "bad"),
    (1, "    missing: 0, checksum invalid: 1, size invalid: 0, other: 0", "bad"),
    (2, "$ scripts/drill.sh          ->  FAILED (as it should)", "bad"),
    (2, "alerts firing: BackupVerifyFailed, RestoreDrillFailed", "warn"),
    (3, "# original file restored  ->  verify and drill pass again", "ok"),
], "reports/verify-damaged.log (excerpt)"), [
    S("Disaster three is the scary one: bit rot. The test overwrites four kilobytes inside one backup file, keeping the same size, so nothing looks wrong from the outside."),
    S("The nightly verification reads every file and checks its checksum: one invalid checksum, in exactly that backup."),
    S("The drill fails too, as it should, and two alerts fire: backup verify failed, and restore drill failed."),
    S("When the original file is put back, verification and the drill pass again. You learn about the damage on a normal morning, not during an incident."),
])

scene(None, "Disasters 4 and 5", "A lost key, and a lost disk", terminal([
    (0, "# wrong encryption passphrase on the backup host", "dim"),
    (0, "ERROR: [075]: no backup set found to restore", "bad"),
    (0, "[restore-drill] FAILED at step: restore from repository    ->  RestoreDrillFailed", "bad"),
    (1, "# right passphrase back  ->  drill passes, alert resolved", "ok"),
    (2, "# the database volume is deleted (disk lost)", "dim"),
    (2, "$ scripts/recover-lost-db.sh   ->  rebuilt from the backups in 16 s", "ok"),
    (3, "# an empty database started by mistake: its WAL was refused (system-id … do not match)", "warn"),
], "reports/drill-wrong-key.log + e2e results"), [
    S("Disaster four: the encryption passphrase is wrong, or lost. Nothing can be restored, the drill fails, and the restore drill failed alert fires. That is exactly what you want to know before the day you need the backup. So keep the passphrase in a vault, outside the server."),
    S("With the right passphrase back, the drill passes and the alert resolves."),
    S("Disaster five: the database volume is deleted, as if the disk died. One command rebuilds the database from the backups, in sixteen seconds, with every archived order back."),
    S("And one more safety check: when an empty database was started by mistake, the repository refused its WAL, because the system identifier did not match. A new database can never overwrite the old backups."),
])

scene(None, "Security, tested", "The isolation is tested, not assumed", checklist([
    (0, "1", "db and app cannot resolve the storage", "the backup host can (HTTP 200)"),
    (1, "2", "Raw backup files", "0 readable order strings: encrypted at rest"),
    (2, "3", "The database's pgBackRest config", "0 S3 keys, 0 passphrases"),
    (3, "4", "S3 without credentials", "403"),
]), [
    S("The security design is tested too. The database and the application cannot even resolve the storage host name. Only the backup host can reach it."),
    S("The raw backup files are searched for order data: zero readable order strings."),
    S("The database's own pgBackRest configuration contains zero storage keys and zero passphrases."),
    S("And the storage without credentials answers 403, forbidden."),
])

# ---------------------------------------------------------------- 9. Testing
scene("Testing", "Proof on every push", "Three test layers in GitHub Actions", checklist([
    (0, "1", "Static", "ShellCheck, yamllint, ruff, 7 pytest tests, hadolint, promtool config + 6 alert test groups"),
    (1, "2", "Image", "Trivy: 0 fixable HIGH/CRITICAL (after replacing the base image's gosu)"),
    (2, "3", "End-to-end, 11 sections", "every disaster above, in one run: 898 s, exit 0"),
    (3, "✓", "Same test in CI", "first backup 62 s · PITR 108/108 in 17 s · outage 0 missing · volume rebuilt in 20 s"),
]), [
    S("All of this runs in GitHub Actions, on every push and every week. First, static checks: ShellCheck, yamllint, ruff, seven pytest tests, hadolint for the Dockerfile, and unit tests for the alert rules."),
    S("Second, the image is scanned with Trivy. It found a vulnerable gosu binary in the PostgreSQL base image, with one critical and 21 high vulnerabilities. It was replaced with a small shim, and the scan is now clean."),
    S("Third, the end to end test, with eleven sections: every disaster you just saw, in one run. The clean run took 898 seconds, and every section passed."),
    S("And the same test passed in CI, on a fresh GitHub runner. There, the first backup took 62 seconds, the recovery brought back 108 of 108 orders in 17 seconds, the outage lost nothing, and the lost volume was rebuilt in 20 seconds."),
])

scene(None, "Honest findings", "What the tests found", notes([
    (0, "pytest", "the WAL segment metric lost precision: the timeline was shifted beyond what a float holds"),
    (1, "promtool", "RestoreTooSlow showed the wrong value; WalArchivingFailing printed fractional counts"),
    (2, "Trivy", "the base image's gosu: 1 CRITICAL + 21 HIGH, replaced"),
    (3, "Not tested", "production-size data, real cloud S3, high availability"),
]), [
    S("The tests found four real problems. The unit tests found that the WAL segment metric lost precision, because the timeline was shifted into bits a float cannot hold exactly."),
    S("The alert rule tests found that one alert summary showed the wrong value, and another printed fractional failure counts."),
    S("And Trivy found the vulnerable gosu binary."),
    S("And to be honest about what was not tested: the lab database is about 30 megabytes, the lab uses SeaweedFS instead of real cloud S3, and high availability is out of scope."),
])

# ---------------------------------------------------------------- 10. Run it yourself
scene("Run it yourself", "Hands-on lab", "The whole stack on your laptop", terminal([
    (0, f"$ git clone https://{REPO}.git", "cmd"),
    (0, "$ cd sufyan-devops-postgres-backup-drills", "cmd"),
    (1, "$ scripts/up.sh                 # secrets, certificates, start, first full backup (~1 min)", "cmd"),
    (2, "$ scripts/status.sh             # the repository + the last drill", "cmd"),
    (2, "$ scripts/drill.sh              # a restore drill, now", "cmd"),
    (2, "$ scripts/backup.sh incr        # a backup, now (full | diff | incr)", "cmd"),
    (3, "$ scripts/pitr.sh \"2026-10-03 14:05:00+00\"   # point-in-time recovery", "cmd"),
    (3, "$ scripts/recover-lost-db.sh    # rebuild a lost database from the backups", "cmd"),
    (4, "Grafana: http://localhost:3000     Prometheus: http://localhost:9090", "ok"),
    (4, "$ scripts/down.sh               # stop (data kept); --purge deletes everything", "cmd"),
], "your terminal"), [
    S("Now let us make it practical. You need Docker with Compose, Bash and OpenSSL. Git Bash on Windows works. And about two gigabytes of disk and memory. Clone the repository and go into the folder."),
    S("Up dot S-H creates the secrets and the certificates, starts everything, and waits for the first full backup. That takes about a minute."),
    S("Status shows what is in the repository and the result of the last drill. Drill runs a restore drill right now, and backup takes a full, differential or incremental backup."),
    S("And now the fun part: drop a table yourself, and undo it with pitr dot S-H and a time stamp. Or delete the database volume, and rebuild it with recover lost D-B."),
    S("Grafana runs on localhost port 3000, and Prometheus on 9090. The whole proof, with every disaster, is scripts slash E-2-E dot S-H, about fifteen minutes. And down dot S-H stops everything."),
])

# ---------------------------------------------------------------- 11. Production
scene("Production on AWS S3", "Real servers", "From the lab to production", checklist([
    (0, "1", "Point it at AWS S3", "S3_ENDPOINT=s3.<region>.amazonaws.com · S3_PORT=443 · S3_URI_STYLE=host"),
    (1, "2", "Credentials", "the IAM user's keys in .secrets/, or an instance role (repo1-s3-key-type=auto)"),
    (2, "3", "Protect the bucket", "Object Lock or versioning against deletion"),
    (3, "4", "Keep the passphrase outside", "a password manager or vault, never only on the server"),
    (4, "5", "Watch the alerts", "route them to the on-call channel; read the drill result every morning"),
]), [
    S("Moving to production is a configuration change. Point the S3 endpoint at your AWS region, use port 443 and host style addressing, and remove the lab's storage container."),
    S("Put the IAM keys into the secrets folder, or better, let pgBackRest use an instance role."),
    S("Protect the bucket with Object Lock or versioning, so deleted or overwritten backups can be recovered."),
    S("Keep the encryption passphrase in a password manager or a vault, outside the server. You saw what happens without it."),
    S("And route the alerts to your on call channel. The drill result on the dashboard is the first thing to check every morning."),
])

scene("Limits", "Honest limits", "What this does not do", notes([
    (0, "Single database server", "replicas and failover are a separate concern"),
    (1, "One storage container in the lab", "production needs durable, off-site, versioned storage"),
    (2, "Drill size", "very large databases need a dedicated drill server"),
    (3, "Next steps", "a second repository in another region, Object Lock, Alertmanager, CloudNativePG"),
]), [
    S("Let us be honest about the limits. This is a single database server. High availability, with replicas and failover, is a separate concern."),
    S("The lab's object storage is one container. Production needs durable storage, ideally off site and versioned or immutable."),
    S("The drill restores onto the backup host. For very large databases, run it on a dedicated drill server with enough disk."),
    S("And next on the list: a second repository in another region for three two one backups, Object Lock, alert routing with Alertmanager, and a Kubernetes version with CloudNativePG and the same drill."),
])

scene(None, "Thanks for watching", "Backups you can trust", svg(
    box(0, 160, 60, 1400, 170, "🛡️", "The setup", ["WAL every 60 s · daily drill · verify · 11 alerts · one-command PITR"], "ok", "#0f2a22")
    + box(1, 160, 290, 1400, 170, "📚", "Code + free study guide + PDF", [f"{REPO}"], "sky")
    + box(2, 160, 500, 1400, 170, "💬", "Your turn", ["when did you last restore a backup? tell me in the comments"], "amber")
), [
    S("That is the project. A backup is only real once it has been restored, and this setup restores one every single day, measures how long it takes and how much data it would lose, and alerts when anything is wrong."),
    S("The code, the documentation and a free study guide, with hands-on labs and interview questions, are linked in the description. Clone it, run up dot S-H, and try to break it."),
    S("Now I would like to hear from you: when did you last restore one of your backups? Tell me in the comments. And if this helped, subscribe for more real DevOps projects. Thanks for watching."),
])
