#!/usr/bin/env bash
# Checks every file in the backup repository against its checksum (runs nightly at 03:00 UTC).
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Verifying the backup repository"
on_backup run-verify
