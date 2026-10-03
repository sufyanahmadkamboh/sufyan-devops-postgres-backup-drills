#!/usr/bin/env bash
# What is in the repository, and how did the last drill go?
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

on_backup pgbackrest --stanza=main info
echo
log "Last restore drill"
compose exec -T backup curl -fsS http://pushgateway:9091/metrics \
  | grep -E '^restore_drill_[a-z_]+\{' | sed -E 's/\{[^}]*\}//' || echo "  no drill has run yet"
