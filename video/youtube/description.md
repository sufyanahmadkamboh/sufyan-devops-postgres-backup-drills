Most teams have backups. Far fewer know that their backups restore. In this full DevOps project I run PostgreSQL 18 with production-grade continuous backups: pgBackRest archives every change to encrypted S3 storage within a minute, a restore drill restores the latest backup every day, checks it against the live database and measures RTO and RPO, 11 alert rules watch every way backups can silently fail, and one command undoes a DROP TABLE to the second before it happened. Then I break it five ways and show the measured results.

💻 Code: https://github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills
📚 Free study guide (PDF, hands-on labs, interview questions): https://github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills/tree/main/study
📈 Measured test results: https://github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills/blob/main/docs/test-results.md
🌐 All my projects: https://sufyanahmadkamboh.github.io/

🧪 Run it on your laptop (Docker with Compose, Bash, OpenSSL; Git Bash on Windows works):
git clone https://github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills.git
cd sufyan-devops-postgres-backup-drills && scripts/up.sh
scripts/status.sh · scripts/drill.sh · scripts/backup.sh incr · scripts/pitr.sh "<time>" · scripts/recover-lost-db.sh
scripts/e2e.sh (every disaster, about 15 minutes) · scripts/down.sh --purge

⏱️ Chapters
0:00 The question
1:35 The problem
2:21 The idea
3:09 Architecture
4:36 The tools
5:55 Restore drills
7:15 Monitoring
8:17 Disasters, measured
11:52 Testing
13:23 Run it yourself
14:23 Production on AWS S3
15:01 Limits

🧰 Tools used, and what each one does here
• PostgreSQL 18: the database being protected (WAL archiving, archive_timeout=60)
• pgBackRest 2.59: encrypted, block-incremental backups, async WAL archiving, delta restore, verify
• S3-compatible object storage (SeaweedFS in the lab, AWS S3 in production)
• supercronic: the backup, verify and drill schedule
• amcheck: corruption check of the restored copy
• Prometheus + Pushgateway + postgres_exporter: drill, backup and archiver metrics, 11 alert rules unit-tested with promtool
• Grafana: a dashboard as code that answers "can we restore right now?"
• Docker Compose: three isolated networks, secrets, mutual TLS with a private CA
• GitHub Actions: static checks, Trivy image scan, and the full 11-section end-to-end test

📊 Measured
• Empty machine → first full backup: 68 s
• Daily restore drill: 6 s, 0 missing orders, amcheck clean
• DROP TABLE orders → PITR: back in service in 10 s, 123/123 orders back, 0 rows from after the target
• Object storage down ~3.5 min: alert after 198 s, archive caught up 35 s after recovery, 0 orders lost
• Bit rot in one backup file: verify "checksum invalid: 1", drill failed, 2 alerts fired
• Wrong encryption passphrase: nothing restorable, RestoreDrillFailed fired
• Database volume deleted: rebuilt from S3 in 16 s

💬 Tell me in the comments: when did you last restore one of your backups?

#PostgreSQL #DevOps #DatabaseReliability
