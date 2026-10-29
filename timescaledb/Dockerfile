FROM postgres:17.11-bookworm@sha256:839fbb5a4942a7758dd93e18b42ea5649807491a0545b5eeeb8f0b8bb11857a5

# Install dependencies for the TimescaleDB APT repository
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && rm -rf /var/lib/apt/lists/*

# Expected TimescaleDB repository signing key fingerprint
ARG TIMESCALEDB_GPG_FINGERPRINT=1005FB68604CE9B8F6879CF759F18EDF47F24417

# Download and verify the repository signing key
RUN set -eu; \
    curl -fsSL \
        https://packagecloud.io/timescale/timescaledb/gpgkey \
        -o /tmp/timescaledb.asc; \
    actual_fingerprint="$( \
        gpg --batch --show-keys --with-colons /tmp/timescaledb.asc \
        | awk -F: '$1 == "fpr" {print $10; exit}' \
    )"; \
    echo "Expected fingerprint: ${TIMESCALEDB_GPG_FINGERPRINT}"; \
    echo "Actual fingerprint:   ${actual_fingerprint}"; \
    test "${actual_fingerprint}" = "${TIMESCALEDB_GPG_FINGERPRINT}"; \
    gpg --batch --yes --dearmor \
        -o /usr/share/keyrings/timescaledb.gpg \
        /tmp/timescaledb.asc; \
    chmod 644 /usr/share/keyrings/timescaledb.gpg; \
    rm /tmp/timescaledb.asc

# Configure TimescaleDB APT repository
RUN echo \
    "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/debian/ bookworm main" \
    > /etc/apt/sources.list.d/timescaledb.list

# Install TimescaleDB 2.19.3 for PostgreSQL 14
RUN set -eu; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        'timescaledb-2-loader-postgresql-17=2.19.3~debian12' \
        'timescaledb-2-2.19.3-postgresql-17=2.19.3~debian12' \
    && rm -rf /var/lib/apt/lists/*

# Preload TimescaleDB when PostgreSQL starts
CMD ["postgres", "-c", "shared_preload_libraries=timescaledb"]

# Run initialization SQL when creating a new database
COPY timescaledb/init.sql /docker-entrypoint-initdb.d/
