#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 -U postgres -v app_password="$P1_DB_PASSWORD" -v temporal_password="$P1_TEMPORAL_PASSWORD" <<'SQL'
CREATE ROLE p1_temporal LOGIN PASSWORD :'temporal_password';
CREATE ROLE p1_app LOGIN PASSWORD :'app_password';
CREATE DATABASE temporal OWNER p1_temporal;
CREATE DATABASE temporal_visibility OWNER p1_temporal;
CREATE DATABASE mingjing;
REVOKE CONNECT ON DATABASE temporal, temporal_visibility, mingjing FROM PUBLIC;
GRANT CONNECT ON DATABASE mingjing TO p1_app;
SQL
psql -v ON_ERROR_STOP=1 -U postgres -d mingjing -f /docker-entrypoint-initdb.d/mingjing.schema
