#!/usr/bin/env bash
# Creates everything secret, once, in .secrets/ (git-ignored):
#   passwords for postgres, app, monitor and Grafana; S3 keys; the repository encryption passphrase;
#   a private CA and TLS certificates for s3, db and backup (pgBackRest uses mutual TLS between hosts).
# Existing files are kept, so re-running is safe. Delete .secrets/ to start over.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

S="$ROOT/.secrets"
mkdir -p "$S/certs"

secret() {  # name length
  if [[ ! -s "$S/$1" ]]; then
    # finite input (no SIGPIPE): 96 random bytes -> letters and digits -> first N characters
    openssl rand -base64 96 | LC_ALL=C tr -dc 'A-Za-z0-9' | cut -c1-"$2" | tr -d '\n' > "$S/$1"
    log "created .secrets/$1"
  fi
}

secret postgres_password 32
secret app_password 32
secret monitor_password 32
secret grafana_admin_password 24
secret s3_access_key 20
secret s3_secret_key 40
secret repo_cipher_pass 64

if [[ ! -s "$S/s3_identities.json" ]]; then
  cat > "$S/s3_identities.json" <<EOF
{
  "identities": [
    {
      "name": "pgbackrest",
      "credentials": [{"accessKey": "$(cat "$S/s3_access_key")", "secretKey": "$(cat "$S/s3_secret_key")"}],
      "actions": ["Read:pgbackrest", "Write:pgbackrest", "List:pgbackrest", "Tagging:pgbackrest"]
    }
  ]
}
EOF
  log "created .secrets/s3_identities.json"
fi

# openssl on Windows (Git Bash) needs C:/... paths; on Linux ROOT_NATIVE is the same as ROOT.
C="$ROOT_NATIVE/.secrets/certs"
CA_KEY="$ROOT_NATIVE/.secrets/ca.key"   # kept OUT of certs/, which is mounted into containers
export MSYS_NO_PATHCONV=1
if [[ ! -s "$C/ca.crt" ]]; then
  openssl req -x509 -newkey rsa:3072 -sha256 -days 825 -nodes -subj "/CN=pg-backup-drills CA" \
    -keyout "$CA_KEY" -out "$C/ca.crt" 2>/dev/null
  log "created the private CA"
fi
for host in s3 db backup; do
  [[ -s "$C/$host.crt" ]] && continue
  openssl req -newkey rsa:3072 -sha256 -nodes -subj "/CN=$host" -keyout "$C/$host.key" -out "$C/$host.csr" 2>/dev/null
  printf 'subjectAltName=DNS:%s,DNS:localhost\nextendedKeyUsage=serverAuth,clientAuth\n' "$host" > "$C/$host.ext"
  openssl x509 -req -sha256 -days 825 -in "$C/$host.csr" -CA "$C/ca.crt" -CAkey "$CA_KEY" -CAserial "$ROOT_NATIVE/.secrets/ca.srl" -CAcreateserial \
    -extfile "$C/$host.ext" -out "$C/$host.crt" 2>/dev/null
  rm -f "$C/$host.csr" "$C/$host.ext"
  log "created TLS certificate for $host"
done

# Containers read these files as their own non-root users (SeaweedFS runs as `seaweed`, PostgreSQL as
# `postgres`), so the directory must be traversable (0711: others can open known files but cannot list it).
# The CA key is never mounted anywhere and stays private.
# (Files only: a glob like "$S"/* would also match certs/ and strip the directory's execute bit.)
find "$S" -type f -exec chmod 0644 {} + 2>/dev/null || true
chmod 0711 "$S" 2>/dev/null || true
chmod 0755 "$S/certs" 2>/dev/null || true
chmod 0600 "$S/ca.key" 2>/dev/null || true
ok "secrets and certificates are in .secrets/ (never committed)"
