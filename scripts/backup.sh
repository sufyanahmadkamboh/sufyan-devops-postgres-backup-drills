#!/usr/bin/env bash
# Takes a backup now: scripts/backup.sh full|diff|incr   (default: incr)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

type="${1:-incr}"
log "Taking a $type backup"
on_backup run-backup "$type"
