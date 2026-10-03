#!/usr/bin/env bash
# Runs a restore drill now (the same one that runs every night at 04:00 UTC).
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Restore drill: restore the latest backup into a scratch copy and check it"
on_backup restore-drill
