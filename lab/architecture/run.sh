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
# Only these two read-only test identities are reproducible on both disposable runners.
# All application, owner, administrator and workflow credentials are random and route-local.
export MJLAB_CI_RUN=${GITHUB_RUN_ID:?} MJLAB_ROUTE="$route"
peer_role="audit_${route}_${MJLAB_CI_RUN}"
peer_password=$(printf '%s' "$peer_role/$GITHUB_SHA" | sha256sum | cut -d' ' -f1)
dc exec -T db psql -U postgres -d "$P2_PROJECT" -v ON_ERROR_STOP=1 -v who="$peer_role" -v dbname="$P2_PROJECT" -v pass="$peer_password" <<'SQL'
CREATE ROLE :"who" LOGIN PASSWORD :'pass';
GRANT CONNECT ON DATABASE :"dbname" TO :"who";
GRANT SELECT ON probe_witness TO :"who";
SQL
dc run --rm -T --no-deps -e MJLAB_CI_RUN -e MJLAB_ROUTE -e GITHUB_SHA -e LAB_PROBE_DB="$P2_PROJECT" -v "$fixture/peer_probe.py:/probe.py:ro" test python /probe.py
echo "LIVE_PREFLIGHT route=$route database_and_history_survived_replacement=true"
if [[ -f "$fixture/experiment.sh" ]]; then
  source "$fixture/experiment.sh"
fi
if [[ ! -f "$fixture/experiment.sh" ]]; then source "$fixture/model.sh"; fi
