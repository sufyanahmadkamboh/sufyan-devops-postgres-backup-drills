"Do we have backups?" Yes. ✅
"When did we last restore one?" …silence. 😬

That silence is how most data-loss stories begin. The backup job says "success" every night, nobody tries a restore, and on the bad day we find out:
👉 the files are damaged
👉 the encryption key is gone
👉 the last good backup is a day old
👉 the restore takes hours, not minutes

So I built a PostgreSQL setup that treats backups like a fire drill 🧯 It doesn't just make backups. It PROVES they work, every single night:

1️⃣ Take the newest backup
2️⃣ Restore it into a throwaway copy
3️⃣ Compare the copy with the real database (any orders missing? any corruption?)
4️⃣ Report the result on a dashboard, and raise an alert if anything is wrong

Every change is also saved to encrypted cloud-style storage within a minute. So if someone runs DROP TABLE at 14:05, one command brings the database back to 14:04:59.

🧪 I broke it on purpose, 6 different ways (local lab):
💥 Dropped the orders table → back in 10 s, 123 of 123 orders restored
💽 Deleted the whole database disk → rebuilt from the backups in 16 s
🪣 Took the backup storage offline → the database kept working, an alert fired, 0 orders lost
🦠 Damaged one backup file (4 KB of random bytes) → caught by the checksum check and the drill, 2 alerts
🔑 Tried a wrong encryption key → nothing restorable, alert fired (lesson: store the key somewhere safe!)
🧯 Nightly restore drill → 6 seconds, 0 missing orders, no corruption

🔒 And the database server itself can't even reach its backups (separate network), so an attacker who breaks into it can't delete them.

📚 New to databases or DevOps? I wrote a free study guide for this project: PostgreSQL, WAL and point-in-time recovery, pgBackRest, S3, Docker Compose, Prometheus and Grafana, explained from zero, with 10 hands-on labs and 25 interview questions (49-page PDF).

👉 Swipe through the slides for the full picture.

💻 Code + study guide: https://github.com/sufyanahmadkamboh/sufyan-devops-postgres-backup-drills
🌐 Slides + all my projects: https://sufyanahmadkamboh.github.io/#story=postgres-backup-drills&slide=1

Honest question: when did YOUR team last restore a backup? 👇

#DevOps #PostgreSQL #DisasterRecovery #Backup #SRE #DatabaseReliability #Docker #Prometheus #Grafana #LearningDevOps
