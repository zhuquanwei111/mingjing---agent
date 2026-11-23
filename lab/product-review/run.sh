#!/usr/bin/env bash
set -euo pipefail
export LAB_DIR="$PWD/lab/product-review" LAB_OUT TEST_HEAD CI_RUN
export P2_PROJECT="whole_$(openssl rand -hex 6)"
for var in P2_BOOTSTRAP_PASSWORD P2_MIGRATION_PASSWORD P2_APP_PASSWORD P2_TEMPORAL_PASSWORD PRODUCT_PASS WITNESS_PASS; do
  export "$var=$(openssl rand -hex 20)"
done
install -d -m 0777 "$LAB_OUT"
dc() { docker compose -p "$P2_PROJECT" -f core/infra/compose.yaml -f lab/architecture/pg-auth.yml -f "$LAB_DIR/compose.yml" "$@"; }
cleanup() {
  status=$?
  dc logs --no-color provider > "$LAB_OUT/provider.log" 2>&1 || true
  dc down -v --remove-orphans >/dev/null || true
  exit "$status"
}
trap cleanup EXIT
[[ "$(git rev-parse HEAD)" == "$TEST_HEAD" ]]
docker build -q -t "$P2_PROJECT-round" lab/architecture/b
dc up -d --wait db temporal witness-db
dc run --rm --no-deps namespace
dc exec -T db psql -U postgres -v ON_ERROR_STOP=1 -v who="$P2_PROJECT" -v pass="$PRODUCT_PASS" <<'SQL'
CREATE ROLE :"who" LOGIN PASSWORD :'pass';
CREATE DATABASE :"who" OWNER :"who";
REVOKE CONNECT ON DATABASE :"who" FROM PUBLIC;
SQL
dc up -d --wait provider
{
  uname -sm
  docker version --format '{{.Server.Version}}'
  docker compose version
  git rev-parse HEAD
  sha256sum lab/architecture/b/linux-amd64.lock lab/product-review/PLAN.md
  dc images
  dc exec -T provider python -VV
  dc exec -T provider python -m pip freeze
  dc exec -T db psql -At -U postgres -c 'SHOW server_version'
} | tee "$LAB_OUT/versions.txt"
dc run --rm -T --no-deps controller | tee "$LAB_OUT/experiment.log"
python3 - "$LAB_OUT" <<'PY'
import base64, gzip, hashlib, pathlib, sys
p=pathlib.Path(sys.argv[1])
for f in [p/"raw.jsonl",p/"versions.txt",*sorted(p.glob("*-history.json"))]:
    raw=f.read_bytes()
    print("PRODUCT_COPY",f.name,hashlib.sha256(raw).hexdigest(),base64.b64encode(gzip.compress(raw,mtime=0)).decode())
PY
