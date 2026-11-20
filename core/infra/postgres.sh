#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 -U postgres -v owner="$P2_MIGRATION_PASSWORD" -v app="$P2_APP_PASSWORD" -v engine="$P2_TEMPORAL_PASSWORD" <<'SQL'
CREATE ROLE p2_owner LOGIN PASSWORD :'owner';
CREATE ROLE p2_app LOGIN PASSWORD :'app';
CREATE ROLE p2_temporal LOGIN PASSWORD :'engine';
CREATE DATABASE mingjing OWNER p2_owner;
CREATE DATABASE temporal OWNER p2_temporal;
CREATE DATABASE temporal_visibility OWNER p2_temporal;
REVOKE CONNECT ON DATABASE mingjing, temporal, temporal_visibility FROM PUBLIC;
GRANT CONNECT ON DATABASE mingjing TO p2_app;
SQL
psql -v ON_ERROR_STOP=1 -U postgres -d mingjing <<'SQL'
GRANT USAGE ON SCHEMA public TO p2_app;
ALTER DEFAULT PRIVILEGES FOR ROLE p2_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO p2_app;
ALTER DEFAULT PRIVILEGES FOR ROLE p2_owner IN SCHEMA public
    GRANT SELECT, USAGE ON SEQUENCES TO p2_app;
SQL
