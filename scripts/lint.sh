#!/usr/bin/env bash
# Every static check, in the order CI runs them. Needs: shellcheck, python3 (pytest, ruff, yamllint), docker.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export MSYS_NO_PATHCONV=1
HERE="$(pwd -W 2>/dev/null || pwd)"

step() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

step "ShellCheck (scripts and container scripts)"
shellcheck -S style -x scripts/*.sh image/bin/entrypoint image/bin/init-stanza image/bin/run-backup \
  image/bin/run-verify image/bin/restore-drill image/bin/loadgen image/bin/pushmetrics image/initdb/*.sh

step "yamllint"
yamllint --strict .

step "ruff + unit tests (metrics exporter)"
ruff check tests image/bin/backup-metrics
python3 -m pytest -q tests

step "hadolint (Dockerfile)"
docker run --rm -i hadolint/hadolint:v2.15.1 hadolint --failure-threshold warning - < image/Dockerfile

step "Prometheus config, alert rules and their unit tests"
docker run --rm -v "$HERE:/w" -w /w --entrypoint promtool prom/prometheus:v3.15.0 check config deploy/prometheus/prometheus.yml
docker run --rm -v "$HERE:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules backups.test.yml

step "Compose file and dashboard"
mkdir -p .secrets/certs
for f in postgres_password app_password monitor_password s3_access_key s3_secret_key s3_identities.json repo_cipher_pass grafana_admin_password; do
  [[ -e ".secrets/$f" ]] || : > ".secrets/$f"
done
docker compose -f deploy/compose.yaml config --quiet
python3 -m json.tool deploy/grafana/dashboards/backups.json > /dev/null
echo "all static checks passed"
