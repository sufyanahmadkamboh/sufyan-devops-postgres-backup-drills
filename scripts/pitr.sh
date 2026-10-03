#!/usr/bin/env bash
# Point-in-time recovery of the LIVE database (for example after a wrong DELETE or DROP TABLE).
#   scripts/pitr.sh "2026-10-03 14:05:00+00"          asks for confirmation
#   scripts/pitr.sh "2026-10-03 14:05:00+00" --yes    no question (automation, tests)
#
# 1. Archive every change made so far (so nothing before the target is lost).
# 2. Stop the application and the database.
# 3. Restore the database to the moment just before the target (pgBackRest delta restore:
#    only changed files are copied), replaying archived WAL up to the target, then promote.
# 4. Start the database, wait until it accepts writes, start the application again.
# Everything after the target time is discarded: pick the time just before the mistake.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

target="${1:?usage: scripts/pitr.sh \"YYYY-MM-DD HH:MM:SS+00\" [--yes]}"
if [[ "${2:-}" != "--yes" ]]; then
  read -r -p "Restore the LIVE database to $target and discard every change after it? Type 'restore': " answer
  [[ "$answer" == "restore" ]] || die "cancelled"
fi

start=$(date +%s)
log "1/4 Archiving the latest changes"
if sql "select pg_switch_wal()" >/dev/null 2>&1; then
  on_backup pgbackrest --stanza=main check >/dev/null || die "WAL could not be archived; refusing to restore"
else
  log "    database is not running: using what is already archived"
fi

log "2/4 Stopping the application and the database"
compose stop app db

log "3/4 Restoring to $target"
compose run --rm --no-deps -e ROLE=restore db --type=time "--target=$target" --target-action=promote \
  || die "restore failed; the database volume may be incomplete: run the restore again"

log "4/4 Starting the database"
compose up -d db
wait_for 600 sql "select 1" >/dev/null || die "database did not come back"
promoted() { [[ "$(sql 'select pg_is_in_recovery()')" == "f" ]]; }
wait_for 600 promoted >/dev/null || die "database did not finish recovery"
compose up -d app
ok "Database restored to $target in $(( $(date +%s) - start )) s (new timeline: $(sql "select timeline_id from pg_control_checkpoint()"))"
log "Take a new full backup soon: scripts/backup.sh full"
