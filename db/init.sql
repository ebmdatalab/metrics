-- This script runs in the context of the metrics database.
-- That's because the Docker Compose configuration for the db service
-- creates and configures this the metrics database as default...
CREATE DATABASE grafana;

-- ... so this extension only gets installed in the metrics database as intended.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- set up the grafanareader role with select permissions by default
CREATE ROLE grafanareader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafanareader;
ALTER USER grafanareader WITH PASSWORD 'grafana';
GRANT CONNECT ON DATABASE metrics TO grafanareader;
GRANT USAGE ON SCHEMA public TO grafanareader;
