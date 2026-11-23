#!/usr/bin/env bash
set -euo pipefail
route=${1:?supply route}
[[ "$route" = a || "$route" = b ]]
root=$(pwd)
fixture="$root/lab/architecture"
export P2_PROJECT="mjlab_${route}_$(openssl rand -hex 7)"
export MJLAB_RUN=${P2_PROJECT##*_}
export P2_BOOTSTRAP_PASSWORD=$(openssl rand -hex 20)
export P2_MIGRATION_PASSWORD=$(openssl rand -hex 20)
export P2_APP_PASSWORD=$(openssl rand -hex 20)
export P2_TEMPORAL_PASSWORD=$(openssl rand -hex 20)
export MJLAB_DB_PASSWORD=$(openssl rand -hex 20)
dc() { docker compose -p "$P2_PROJECT" -f core/infra/compose.yaml -f "$fixture/pg-auth.yml" "$@"; }
cleanup() { dc down -v --remove-orphans >/dev/null; }
trap cleanup EXIT
dc up -d --wait db temporal
dc run --rm --no-deps namespace
# Create a fresh LOGIN/database whose name matches the isolated engine namespace.
dc exec -T db psql -U postgres -v ON_ERROR_STOP=1 -v who="$P2_PROJECT" -v pass="$MJLAB_DB_PASSWORD" <<'SQL'
CREATE ROLE :"who" LOGIN PASSWORD :'pass';
CREATE DATABASE :"who" OWNER :"who";
REVOKE CONNECT ON DATABASE :"who" FROM PUBLIC;
SQL
dc build test
probe() {
  dc run --rm -T --no-deps -e MJLAB_RUN -e MJLAB_DB_PASSWORD -v "$fixture:/probe:ro" test python /probe/verify_runtime.py "$1" "$route"
}
probe write
old_db=$(dc ps -q db)
old_engine=$(dc ps -q temporal)
dc up --no-deps --force-recreate -d --wait db
dc up --no-deps --force-recreate -d --wait temporal
[[ "$old_db" != "$(dc ps -q db)" && "$old_engine" != "$(dc ps -q temporal)" ]]
probe readback
if dc run --rm -T --no-deps --entrypoint env db PGPASSWORD="$(openssl rand -hex 20)" psql -h db -U "$P2_PROJECT" -d "$P2_PROJECT" -c 'select 1' >/dev/null 2>&1; then
  echo "unexpected credential acceptance"; exit 1
fi
echo "LIVE_PREFLIGHT route=$route database_and_history_survived_replacement=true"
if [[ -f "$fixture/experiment.sh" ]]; then
  source "$fixture/experiment.sh"
fi
if [[ ! -f "$fixture/experiment.sh" ]]; then source "$fixture/model.sh"; fi
