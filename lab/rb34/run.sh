#!/usr/bin/env bash
set -euo pipefail
export RB34_DIR="$PWD/lab/rb34" RB34_OUT="${RB34_OUT:?}" TEST_HEAD="${TEST_HEAD:?}" CI_RUN="${CI_RUN:?}"
export P2_PROJECT="rb34_$(openssl rand -hex 7)"
for var in P2_BOOTSTRAP_PASSWORD P2_MIGRATION_PASSWORD P2_APP_PASSWORD P2_TEMPORAL_PASSWORD PRODUCT_PASS WITNESS_PASS; do
  export "$var=$(openssl rand -hex 20)"
done
install -d -m 0777 "$RB34_OUT"
dc() { docker compose -p "$P2_PROJECT" -f core/infra/compose.yaml -f lab/architecture/pg-auth.yml -f "$RB34_DIR/compose.yml" "$@"; }
cleanup() {
  status=$?
  dc logs --no-color experiment-worker provider delivery > "$RB34_OUT/services.log" 2>&1 || true
  if (( status )); then tail -100 "$RB34_OUT/services.log"; fi
  dc down -v --remove-orphans >/dev/null || true
  exit "$status"
}
trap cleanup EXIT
[[ "$(git rev-parse HEAD)" == "$TEST_HEAD" ]]
docker build -q -t "$P2_PROJECT-rb34" lab/architecture/b
dc up -d --wait db temporal witness-db
dc run --rm --no-deps namespace
dc exec -T db psql -U postgres -v ON_ERROR_STOP=1 -v who="$P2_PROJECT" -v pass="$PRODUCT_PASS" <<'SQL'
CREATE ROLE :"who" LOGIN PASSWORD :'pass';
CREATE DATABASE :"who" OWNER :"who";
REVOKE CONNECT ON DATABASE :"who" FROM PUBLIC;
SQL
dc up -d --wait provider delivery
dc up -d experiment-worker
{
  uname -sm
  docker version --format '{{.Server.Version}}'
  docker compose version
  git rev-parse HEAD
  sha256sum lab/architecture/b/linux-amd64.lock lab/rb34/PLAN.md
  dc images
  dc exec -T experiment-worker python -VV
  dc exec -T experiment-worker python -m pip freeze
  dc exec -T db psql -At -U postgres -c 'SHOW server_version'
} | tee "$RB34_OUT/versions.txt"
dc run --rm -T --no-deps controller | tee "$RB34_OUT/experiment.log"
