#!/usr/bin/env bash
# Disaster recovery: the database's data is lost or corrupt (disk failure, deleted volume, new server).
# Rebuilds the database volume from the backups, replaying every archived change, then starts it.
#   scripts/recover-lost-db.sh          asks for confirmation
#   scripts/recover-lost-db.sh --yes    no question (automation, tests)
#
# Important: never just start the database on an empty volume. PostgreSQL would create a new, EMPTY
# database (pgBackRest then refuses its WAL: "system-id do not match" — the backups stay safe).
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

if [[ "${1:-}" != "--yes" ]]; then
  read -r -p "This DELETES the current database volume and restores it from the backups. Type 'recover': " answer
  [[ "$answer" == "recover" ]] || die "cancelled"
fi

project="${COMPOSE_PROJECT_NAME:-pg-backup-drills}"   # the name: set in deploy/compose.yaml
start=$(date +%s)

log "1/4 Stopping the application and the database"
compose stop app db >/dev/null
compose rm -f db >/dev/null

log "2/4 Removing the damaged database volume and its WAL queue"
docker volume rm "${project}_db-data" "${project}_db-spool" >/dev/null 2>&1 || true

log "3/4 Restoring the latest backup + all archived WAL"
compose run --rm --no-deps -e ROLE=restore db --type=default \
  || die "restore failed: do NOT start the db service on the empty volume; fix the cause and run this again"

log "4/4 Starting the database"
compose up -d db
wait_for 900 sql "select 1" >/dev/null || die "database did not come back"
promoted() { [[ "$(sql 'select pg_is_in_recovery()')" == "f" ]]; }
wait_for 900 promoted >/dev/null || die "database did not finish recovery"
compose up -d app
ok "Database recovered from the backups in $(( $(date +%s) - start )) s ($(sql 'select count(*) from orders') orders)"
log "Take a new full backup soon: scripts/backup.sh full"
