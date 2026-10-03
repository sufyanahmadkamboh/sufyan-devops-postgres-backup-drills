#!/usr/bin/env bash
# Shared helpers for the scripts. Only Docker (with Compose v2) and Bash are needed on the host.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export MSYS_NO_PATHCONV=1   # Git Bash on Windows: do not rewrite /paths in docker arguments
# Docker on Windows needs C:/... paths; `pwd -W` only exists in Git Bash.
ROOT_NATIVE="$(cd "$ROOT" && { pwd -W 2>/dev/null || pwd; })"

compose() { docker compose -f "$ROOT_NATIVE/deploy/compose.yaml" "$@"; }

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERR\033[0m %s\n' "$*" >&2; exit 1; }

# Run a command on the backup host / the database (as postgres).
on_backup() { compose exec -T -u postgres backup "$@"; }
on_db()     { compose exec -T -u postgres db "$@"; }
sql()       { on_db psql -d shop -XAtq -v ON_ERROR_STOP=1 -c "$1"; }

# Instant Prometheus query: one "<labels> <value>" line per series.
prom_query() {
  compose exec -T backup python3 -c '
import json, sys, urllib.parse, urllib.request
url = "http://prometheus:9090/api/v1/query?" + urllib.parse.urlencode({"query": sys.argv[1]})
for r in json.load(urllib.request.urlopen(url, timeout=10))["data"]["result"]:
    m = r["metric"]; print(m.get("alertname") or m.get("type") or m.get("__name__") or "value", r["value"][1])
' "$1"
}

# Wait until a command succeeds; prints the seconds it took.
wait_for() {
  local timeout="$1"; shift
  local start; start=$(date +%s)
  until "$@" >/dev/null 2>&1; do
    (( $(date +%s) - start > timeout )) && return 1
    sleep 2
  done
  echo $(( $(date +%s) - start ))
}
