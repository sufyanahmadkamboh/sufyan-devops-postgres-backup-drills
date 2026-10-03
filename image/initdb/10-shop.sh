#!/usr/bin/env bash
# Runs once, when the database volume is empty: creates the shop database, its table and two roles.
#   app      the application (reads/writes orders)
#   monitor  read-only monitoring: postgres_exporter and the restore drill's comparison queries
set -euo pipefail

app_password="$(cat /run/secrets/app_password)"
monitor_password="$(cat /run/secrets/monitor_password)"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v app_password="$app_password" -v monitor_password="$monitor_password" <<'SQL'
CREATE ROLE app LOGIN PASSWORD :'app_password';
CREATE ROLE monitor LOGIN PASSWORD :'monitor_password' IN ROLE pg_monitor;
CREATE DATABASE shop OWNER app;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname shop <<'SQL'
SET ROLE app;
CREATE TABLE orders (
  id         bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  customer   text        NOT NULL,
  amount     numeric(10,2) NOT NULL CHECK (amount >= 0)
);
CREATE INDEX orders_created_at_idx ON orders (created_at);
GRANT SELECT ON orders TO monitor;
SQL
