#!/usr/bin/env bash
# Stops the stack. Data (database, backups, metrics) is kept unless --purge is given.
#   scripts/down.sh            stop, keep volumes
#   scripts/down.sh --purge    stop and DELETE the database, the backup repository and all volumes
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

if [[ "${1:-}" == "--purge" ]]; then
  log "Removing the stack AND all its data"
  compose down --volumes --remove-orphans --timeout 30
else
  log "Stopping the stack (data kept; use --purge to delete it)"
  compose down --remove-orphans --timeout 30
fi
ok "Done"
