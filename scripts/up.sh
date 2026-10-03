#!/usr/bin/env bash
# Starts everything and waits until the first full backup exists.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

"$ROOT/scripts/setup.sh"
log "Building and starting the stack (first start of the object store can take ~2 minutes)"
compose up -d --build --wait --wait-timeout 420

log "Waiting for the backup host to create the stanza and take the first full backup"
has_backup() { on_backup pgbackrest --stanza=main info --output=json | grep -q '"type":"full"\|"type": "full"'; }
if secs=$(wait_for 300 has_backup); then
  ok "First full backup is in the repository (${secs} s)"
else
  compose logs --tail 40 backup
  die "No full backup after 5 minutes"
fi
cat <<'EOF'

  Grafana:     http://localhost:3000  (anonymous view; admin password in .secrets/grafana_admin_password)
  Prometheus:  http://localhost:9090

  Try:  scripts/status.sh      scripts/drill.sh      scripts/backup.sh incr
EOF
