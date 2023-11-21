-- set up the grafanareader role with select permissions by default
CREATE ROLE grafanareader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafanareader;
ALTER USER grafanareader WITH PASSWORD 'grafana';
GRANT CONNECT ON DATABASE metrics TO grafanareader;
GRANT USAGE ON SCHEMA public TO grafanareader;
