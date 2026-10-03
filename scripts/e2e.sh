#!/usr/bin/env bash
# End-to-end test from an empty machine: backups, restore drills, point-in-time recovery after an
# accident, storage outage, damaged backup, lost encryption key, network isolation and monitoring.
# Every number in reports/e2e-results.md is measured by this script.
#   scripts/e2e.sh               everything, from scratch (deletes this stack's data)
#   E2E_FROM=5 scripts/e2e.sh    resume at section 5 on the running stack
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$ROOT" || exit 1

RESULTS="$ROOT/reports/e2e-results.md"
mkdir -p "$ROOT/reports"
if (( ${E2E_FROM:-1} <= 1 )); then
  printf '# End-to-end results (%s)\n' "$(date -u '+%Y-%m-%d %H:%M UTC')" > "$RESULTS"
fi

record()  { echo "$*" >> "$RESULTS"; }
pass()    { ok "$*"; record "- PASS: $*"; }
fail()    { record "- FAIL: $*"; compose logs --tail 30 backup >&2 || true; die "$*"; }
section() { log "$*"; record ""; record "## $*"; }
expect()  {
  local what="$1" got="$2" want="$3"
  if [[ "$got" == "$want" ]]; then pass "$what: $got"; else fail "$what: got '$got', expected '$want'"; fi
}

metric() {  # name -> value from the Pushgateway (first series)
  compose exec -T backup curl -fsS http://pushgateway:9091/metrics | awk -v m="$1" '$1 ~ "^"m"[{ ]" || $1 == m {print $2; exit}'
}
metric_for() {  # name type -> value of the series with that backup type
  compose exec -T backup curl -fsS http://pushgateway:9091/metrics | awk -v m="$1" -v t="type=\"$2\"" 'index($1, m"{") == 1 && index($1, t) {print $2; exit}'
}
firing()  { [[ -n "$(prom_query "ALERTS{alertname=\"$1\",alertstate=\"firing\"}")" ]]; }
resolved(){ [[ -z "$(prom_query "ALERTS{alertname=\"$1\",alertstate=\"firing\"}")" ]]; }
orders()  { sql "select count(*) from orders"; }
now_utc() { sql "select to_char(clock_timestamp() at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS.US') || '+00'"; }

drill() {  # runs a drill; returns its exit code; output in reports/<name>.log
  local name="$1"; shift
  compose exec -T "$@" backup restore-drill > "$ROOT/reports/$name.log" 2>&1
}
record_drill() {
  record "  - drill took $(metric restore_drill_duration_seconds) s (restore $(metric restore_drill_restore_seconds) s)," \
    "restored $(metric restore_drill_restored_rows) orders, missing $(metric restore_drill_missing_rows)," \
    "newest restored order $(metric restore_drill_data_loss_seconds) s behind live, amcheck ok: $(metric restore_drill_amcheck_ok)"
}

# Path of the first bundle file of the newest full backup, as seen by the object store's filer.
newest_full_bundle() {
  local label
  label="$(on_backup sh -c 'pgbackrest --stanza=main info --output=json | python3 -c "import json,sys; print([b[\"label\"] for b in json.load(sys.stdin)[0][\"backup\"] if b[\"type\"] == \"full\"][-1])"')"
  echo "/buckets/pgbackrest/main/backup/main/$label/bundle/1"
}

# ---------------------------------------------------------------------------------------------
s1() {
  section "1. Fresh start"
  scripts/down.sh --purge >/dev/null 2>&1 || true
  local start; start=$(date +%s)
  scripts/up.sh
  pass "stack up, stanza created, WAL archiving checked and first full backup taken in $(( $(date +%s) - start )) s"
}

s2() {
  section "2. Normal operation: the application writes, backups run"
  sleep 30
  local o1; o1="$(orders)"
  sleep 10
  local o2; o2="$(orders)"
  (( o2 > o1 )) || fail "the application is not writing orders"
  pass "application writing: $(( o2 - o1 )) orders in 10 s"
  for t in incr diff incr; do
    on_backup run-backup "$t" > "$ROOT/reports/backup-$t.log" 2>&1 || fail "$t backup failed"
    pass "$t backup: $(grep -oE 'backup size = [^,]+' "$ROOT/reports/backup-$t.log" | head -n1), $(grep -oE 'completed successfully \([0-9]+ms\)' "$ROOT/reports/backup-$t.log" | head -n1)"
  done
  on_backup pgbackrest --stanza=main info > "$ROOT/reports/info.txt"
  record "- repository: $(grep -c 'backup:' "$ROOT/reports/info.txt") backups (see reports/info.txt)"
}

s3() {
  section "3. Restore drill"
  drill drill-1 || fail "restore drill failed (reports/drill-1.log)"
  expect "drill result" "$(metric restore_drill_success)" "1"
  expect "orders missing in the restored copy" "$(metric restore_drill_missing_rows)" "0"
  expect "amcheck (corruption check) on the restored copy" "$(metric restore_drill_amcheck_ok)" "1"
  record_drill
}

s4() {
  section "4. Repository verification"
  on_backup run-verify > "$ROOT/reports/verify-1.log" 2>&1 || fail "verify failed on a healthy repository"
  expect "verify result" "$(metric backup_verify_success)" "1"
  record "  - $(grep -E '^  archiveId' "$ROOT/reports/verify-1.log" | head -n1 | sed 's/^ *//')"
}

s5() {
  section "5. Accident: an order table is dropped; point-in-time recovery"
  local target before start rto
  target="$(now_utc)"
  before="$(sql "select count(*) from orders where created_at <= '$target'")"
  sleep 3
  sql "drop table orders"
  record "- $before orders existed at $target; then: DROP TABLE orders"
  start=$(date +%s)
  scripts/pitr.sh "$target" --yes > "$ROOT/reports/pitr.log" 2>&1 || { tail -30 "$ROOT/reports/pitr.log"; fail "PITR failed"; }
  rto=$(( $(date +%s) - start ))
  expect "orders up to the target after recovery" "$(sql "select count(*) from orders where created_at <= '$target'")" "$before"
  expect "orders after the target (must be gone)" "$(sql "select count(*) from orders where created_at > '$target' and id <= (select max(id) from orders where created_at <= '$target')")" "0"
  pass "database back in service in ${rto} s, on timeline $(sql "select timeline_id from pg_control_checkpoint()")"
  sleep 10
  local o1; o1="$(orders)"; sleep 5
  if (( "$(orders)" > o1 )); then pass "application writing again after recovery"; else fail "application not writing after recovery"; fi
  on_backup run-backup full > "$ROOT/reports/backup-after-pitr.log" 2>&1 || fail "full backup after PITR failed"
  drill drill-after-pitr || fail "drill after PITR failed"
  pass "new full backup + restore drill on the new timeline passed"
  record_drill
}

s6() {
  section "6. Storage outage: the object store goes down"
  local start before_fail o1
  before_fail="$(sql "select failed_count from pg_stat_archiver")"
  o1="$(orders)"
  start=$(date +%s)
  compose stop s3 >/dev/null 2>&1
  record "- object store stopped"
  wait_for 420 firing WalArchivingFailing >/dev/null || fail "WalArchivingFailing did not fire"
  pass "alert WalArchivingFailing firing $(( $(date +%s) - start )) s after the outage started"
  if (( "$(orders)" > o1 )); then
    pass "database kept accepting orders during the outage (WAL queued locally)"
  else
    fail "database stopped accepting orders"
  fi
  record "- archive failures during the outage: $(( $(sql "select failed_count from pg_stat_archiver") - before_fail ))"
  local back; back=$(date +%s)
  compose start s3 >/dev/null 2>&1
  compose up -d --wait s3 >/dev/null 2>&1
  # shellcheck disable=SC2317,SC2329  # called through wait_for
  caught_up() { (( $(sql "select extract(epoch from now() - last_archived_time)::int from pg_stat_archiver") < 90 )); }
  wait_for 300 caught_up >/dev/null || fail "WAL archiving did not recover"
  pass "WAL archiving caught up $(( $(date +%s) - back )) s after the object store came back"
  wait_for 600 resolved WalArchivingFailing >/dev/null || fail "alert did not resolve"
  pass "alert resolved $(( $(date +%s) - back )) s after recovery"
  # Any scheduled backup that ran during the outage failed (and alerted); the next one must work again.
  on_backup run-backup incr > "$ROOT/reports/backup-after-outage.log" 2>&1 || fail "backup after the outage failed"
  expect "incremental backup after the outage" "$(metric_for backup_last_run_success incr)" "1"
  drill drill-after-outage || fail "drill after the outage failed"
  expect "orders missing after the outage (drill)" "$(metric restore_drill_missing_rows)" "0"
  record_drill
}

s7() {
  section "7. A backup file is silently damaged in the object store (bit rot)"
  local f; f="$(newest_full_bundle)"
  compose exec -T s3 sh -c "curl -fsS -o /tmp/orig 'http://localhost:8888$f' \
    && cp /tmp/orig /tmp/rot && dd if=/dev/urandom of=/tmp/rot bs=4096 seek=50 count=1 conv=notrunc 2>/dev/null \
    && curl -fsS -o /dev/null -F file=@/tmp/rot 'http://localhost:8888$f'" || fail "could not damage the test file"
  record "- 4 KiB in the middle of $f overwritten with random bytes (same size)"
  if on_backup run-verify > "$ROOT/reports/verify-damaged.log" 2>&1; then fail "verify did not notice the damage"; fi
  pass "verify detected it: $(grep -m1 -oE 'checksum invalid: [1-9][0-9]*' "$ROOT/reports/verify-damaged.log")"
  if drill drill-damaged; then fail "drill passed on a damaged backup"; fi
  pass "restore drill failed as it should: $(grep -m1 -oE 'zst error: [^]]*\]? ?[A-Za-z ]+' "$ROOT/reports/drill-damaged.log" || echo 'restore failed')"
  wait_for 120 firing BackupVerifyFailed >/dev/null || fail "BackupVerifyFailed alert did not fire"
  wait_for 120 firing RestoreDrillFailed >/dev/null || fail "RestoreDrillFailed alert did not fire"
  pass "alerts BackupVerifyFailed and RestoreDrillFailed firing"
  compose exec -T s3 sh -c "curl -fsS -o /dev/null -F file=@/tmp/orig 'http://localhost:8888$f'" || fail "could not put the file back"
  on_backup run-verify > "$ROOT/reports/verify-repaired.log" 2>&1 || fail "verify still failing after repair"
  drill drill-repaired || fail "drill still failing after repair"
  pass "original file restored: verify and drill pass again"
}

s8() {
  section "8. Lost encryption key"
  if drill drill-wrong-key -e PGBACKREST_REPO1_CIPHER_PASS=not-the-real-key; then fail "drill passed with a wrong key"; fi
  pass "with the wrong passphrase nothing can be restored: $(grep -m1 -oE 'ERROR: \[[0-9]+\]: [^.]*' "$ROOT/reports/drill-wrong-key.log" | cut -c1-110)"
  wait_for 120 firing RestoreDrillFailed >/dev/null || fail "RestoreDrillFailed did not fire"
  pass "alert RestoreDrillFailed firing"
  drill drill-right-key || fail "drill with the right key failed"
  pass "with the right passphrase the drill passes again (keep the passphrase outside this server!)"
  wait_for 120 resolved RestoreDrillFailed >/dev/null || fail "RestoreDrillFailed did not resolve"
  pass "alert RestoreDrillFailed resolved after the passing drill"
}

s9() {
  section "9. Disaster: the database volume is lost"
  local before start
  sql "select pg_switch_wal()" >/dev/null
  on_backup pgbackrest --stanza=main check >/dev/null || fail "could not archive the latest WAL"
  before="$(orders)"
  start=$(date +%s)
  scripts/recover-lost-db.sh --yes > "$ROOT/reports/recover-lost-db.log" 2>&1 \
    || { tail -30 "$ROOT/reports/recover-lost-db.log"; fail "recovery from a lost volume failed"; }
  pass "database volume deleted and rebuilt from the backups in $(( $(date +%s) - start )) s"
  local after; after="$(sql "select count(*) from orders where id <= (select max(id) from orders)")"
  if (( after >= before )); then
    pass "orders after recovery: $after (archived before the loss: $before)"
  else
    fail "orders after recovery: $after, expected at least $before"
  fi
  on_backup run-backup full > "$ROOT/reports/backup-after-recovery.log" 2>&1 || fail "full backup after recovery failed"
  drill drill-after-recovery || fail "drill after recovery failed"
  pass "new full backup + restore drill after the recovery passed"
}

s10() {
  section "10. Security checks"
  reach() { compose exec -T "$1" sh -c "curl -s -m 5 -o /dev/null -w '%{http_code}' --cacert /certs/ca.crt https://s3:8443/healthz 2>/dev/null || echo unreachable" | tail -c 20; }
  expect "object store reachable from the database host" "$(compose exec -T db sh -c 'getent hosts s3 >/dev/null && echo yes || echo no')" "no"
  expect "object store reachable from the application" "$(compose exec -T app sh -c 'getent hosts s3 >/dev/null && echo yes || echo no')" "no"
  expect "object store reachable from the backup host" "$(reach backup)" "200"
  local f plain
  f="$(newest_full_bundle)"
  plain="$(compose exec -T s3 sh -c "curl -fsS 'http://localhost:8888$f' | grep -c -a 'customer-' || true")"
  expect "readable order data in a raw backup file (encryption at rest)" "$plain" "0"
  expect "S3 key or passphrase in the database host's pgBackRest config" \
    "$(compose exec -T db sh -c 'grep -cE "s3-key|cipher-pass" /etc/pgbackrest/pgbackrest.conf || true')" "0"
  expect "S3 without the access key" "$(compose exec -T backup sh -c "curl -s -o /dev/null -w '%{http_code}' --cacert /etc/pgbackrest/tls/ca.crt https://s3:8443/pgbackrest/")" "403"
}

s11() {
  section "11. Monitoring"
  for q in 'restore_drill_success' 'backup_verify_success' 'pgbackrest_backup_last_timestamp_seconds{type="full"}' \
           'pg_stat_archiver_archived_count' 'pgbackrest_stanza_status_code'; do
    [[ -n "$(prom_query "$q")" ]] || fail "Prometheus has no series for $q"
    pass "Prometheus has $q"
  done
  local firing_now; firing_now="$(prom_query 'ALERTS{alertstate="firing"}' | awk '{print $1}' | sort -u | paste -sd, -)"
  record "- alerts firing at the end: ${firing_now:-none}"
  [[ -z "$firing_now" ]] || fail "alerts still firing at the end: $firing_now"
}

for n in 1 2 3 4 5 6 7 8 9 10 11; do
  (( n >= ${E2E_FROM:-1} )) && "s$n"
done
ok "All end-to-end checks passed. Results: reports/e2e-results.md"
