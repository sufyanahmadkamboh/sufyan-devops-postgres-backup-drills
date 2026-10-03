# PostgreSQL 18 with pgBackRest. One image, two roles (set by ROLE):
#   ROLE=db      the database: PostgreSQL + pgBackRest TLS server (WAL archiving goes to the backup host)
#   ROLE=backup  the backup host: pgBackRest TLS server + scheduler (backups, verify, restore drills, metrics)
FROM postgres:18.6

ARG PGBACKREST_VERSION=2.59.2-1.pgdg13+1
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# pgBackRest is pinned (backup format and behaviour must not change by surprise). The small helper
# packages are not: they come from Debian's security updates on every rebuild.
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends \
      "pgbackrest=${PGBACKREST_VERSION}" python3 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# supercronic: cron for containers (logs to stdout, no setuid, exits cleanly on SIGTERM)
RUN curl -fsSL -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
 && echo "${SUPERCRONIC_SHA256}  /usr/local/bin/supercronic" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/supercronic

RUN install -d -o postgres -g postgres -m 0750 /var/log/pgbackrest /var/lib/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest \
 && install -d -o postgres -g postgres -m 0700 /var/lib/drill

COPY --chmod=0755 bin/ /usr/local/bin/
COPY --chmod=0644 crontab /etc/backup.crontab
COPY --chmod=0755 initdb/ /docker-entrypoint-initdb.d/

ENV ROLE=db
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["postgres"]
