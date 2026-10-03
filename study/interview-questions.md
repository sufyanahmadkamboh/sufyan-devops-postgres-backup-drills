# Interview questions

25 questions this project prepares you for. Try to answer before opening the answer.

1. **What is the difference between a backup that runs and a backup that restores?**
   <details><summary>Answer</summary>A job can write files successfully while the result is unusable: damaged objects, missing WAL, a lost encryption key, incompatible versions. Only a restore with checks proves it. That is why this project restores every night and alerts on failure.</details>

2. **Explain RPO and RTO with numbers from this project.**
   <details><summary>Answer</summary>RPO is the acceptable data loss: WAL is archived at least every 60 s (`archive_timeout`), and the drill measures the real gap between live and restored data. RTO is the acceptable restore time: the drill measures it every night; alerts fire above 5 minutes of data loss or 30 minutes of restore time.</details>

3. **What is the WAL and why does it make point-in-time recovery possible?**
   <details><summary>Answer</summary>Every change is written to the WAL before the data files. A base backup plus all WAL since it can be replayed to any moment, stopping just before a chosen time.</details>

4. **How would you undo an accidental `DROP TABLE` at 15:00:05?**
   <details><summary>Answer</summary>Note the last good time (15:00:02), archive the current WAL segment (`pg_switch_wal` + `pgbackrest check`), stop the app and database, run `pgbackrest restore --delta --type=time --target="... 15:00:02+00" --target-action=promote`, start the database (new timeline), start the app, take a new full backup. `scripts/pitr.sh` does exactly this.</details>

5. **Why is a streaming replica not a backup?**
   <details><summary>Answer</summary>It replicates every change immediately, including deletions and corruption. It protects against hardware failure, not against mistakes, attacks or software bugs.</details>

6. **Full, differential, incremental: what does a restore need for each?**
   <details><summary>Answer</summary>Full: just itself. Differential: the full plus the diff. Incremental: the full, the latest diff, and every incremental after it. Plus WAL since the last backup in all cases.</details>

7. **Why use a dedicated backup host instead of running backups on the database server?**
   <details><summary>Answer</summary>Storage credentials and the encryption passphrase stay off the database server, and the database server cannot reach storage at all. A compromised database host cannot read or delete its backups.</details>

8. **What does `archive-async` do and what happens when storage is down?**
   <details><summary>Answer</summary>WAL is queued in a local spool and sent in the background, so `archive_command` returns quickly. When storage is down the queue grows (up to `archive-push-queue-max`), the database keeps running, `WalArchivingFailing` fires, and the queue drains when storage returns.</details>

9. **Why must a test restore use `--archive-mode=off`?**
   <details><summary>Answer</summary>Otherwise the restored copy, after promotion, would archive WAL of a new timeline into the production repository and pollute it.</details>

10. **What does the restore drill check, beyond "the database starts"?**
    <details><summary>Answer</summary>That no orders are missing up to the restored point (compared with the live database through a read-only role), how far behind live the copy is (RPO), and that `pg_amcheck --heapallindexed` finds no corruption in tables and indexes.</details>

11. **How do you detect silent damage in backup storage?**
    <details><summary>Answer</summary>`pgbackrest verify` reads every file and compares checksums. This project runs it nightly and alerts on failure; the lab damages a file in storage to prove it is caught (and that the drill fails too).</details>

12. **What happens if you lose the repository encryption passphrase?**
    <details><summary>Answer</summary>The backups cannot be read at all. Keep a copy outside the servers (password manager, secrets vault), and test it: the lab shows a drill with the wrong key failing.</details>

13. **Why SeaweedFS and not MinIO for a local S3?**
    <details><summary>Answer</summary>MinIO stopped publishing community images in 2025 and the project was archived in 2026. SeaweedFS is maintained and S3-compatible; in production the endpoint points to AWS S3 or another provider without other changes.</details>

14. **How would you protect backups against ransomware?**
    <details><summary>Answer</summary>Credentials only on a separate backup host, network separation, encryption, bucket versioning or Object Lock (immutable for N days), a second copy in another account or region, and drills so you know the restore works.</details>

15. **Why does a batch job push metrics to a Pushgateway?**
    <details><summary>Answer</summary>It runs briefly and exits, so Prometheus cannot scrape it. The Pushgateway holds its last result. Group by labels (here `type`) so results don't overwrite each other.</details>

16. **Why alert on `increase(pg_stat_archiver_failed_count[5m]) > 0` rather than `failed_count > 0`?**
    <details><summary>Answer</summary>Counters never decrease; one old failure would keep the alert firing forever. The increase means "failing right now".</details>

17. **How do you alert on a job that silently stopped running?**
    <details><summary>Answer</summary>Alert on the age of the last success, not on failures: `BackupTooOld`, `FullBackupTooOld`, `RestoreDrillMissing` (including `absent()` when there was never a result).</details>

18. **How do you test alert rules?**
    <details><summary>Answer</summary>`promtool test rules` with input series and expected alerts, including cases that must not fire. In this project the tests caught a rule whose summary showed the wrong value because of how PromQL `and` works.</details>

19. **What is mutual TLS and how is it configured between the hosts here?**
    <details><summary>Answer</summary>Both client and server present certificates signed by a trusted CA. pgBackRest's TLS server is configured with `tls-server-auth=<client-CN>=<stanza>`, so only the `db` certificate may use stanza `main` on the backup host and vice versa.</details>

20. **Why is the CA private key kept out of the mounted certificate directory?**
    <details><summary>Answer</summary>Anyone who reads it can issue certificates every component trusts. Containers only need their own certificate, key and the CA certificate.</details>

21. **Why does the database container stop with SIGINT?**
    <details><summary>Answer</summary>SIGINT is PostgreSQL's fast shutdown. The default SIGTERM (smart shutdown) waits for clients and may be killed by Docker's timeout, leaving `postmaster.pid`; pgBackRest then refuses to restore over it.</details>

22. **What is a timeline and when do you see a new one?**
    <details><summary>Answer</summary>A branch in the database's history. After a point-in-time recovery the database continues on a new timeline (1 → 2), so WAL from the abandoned future and the new one never mix.</details>

23. **How would you move this setup to AWS?**
    <details><summary>Answer</summary>Point the backup host at an S3 bucket (endpoint, region, host-style URIs, IAM role or keys), enable versioning/Object Lock and lifecycle rules, run the database and backup host on separate instances or use the same image on ECS/Kubernetes, and keep the drills and alerts unchanged.</details>

24. **What would you monitor first if you could monitor only three things?**
    <details><summary>Answer</summary>WAL archiving failures/age (continuous protection), age of the newest successful backup, and the result and age of the last restore drill.</details>

25. **How does CI prove the system works?**
    <details><summary>Answer</summary>Static checks (ShellCheck, hadolint, yamllint, ruff, pytest, promtool), a Trivy scan of the image, and an end-to-end test on a fresh runner: backups, drill, verify, PITR after a `DROP TABLE`, a storage outage, a damaged file, a lost key, security and monitoring checks, with every number measured.</details>
