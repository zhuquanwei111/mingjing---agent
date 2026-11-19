#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
root=$(mktemp -d /tmp/mingjing-p1-rebuild.XXXXXX)
cp -R .dockerignore infra requirements src tests "$root/"
cd "$root"
sh infra/new-run.sh
trap 'sh infra/compose.sh down --volumes >/dev/null 2>&1' EXIT
sh infra/compose.sh up -d --wait temporal
sh infra/compose.sh run --rm --no-deps namespace
sh infra/compose.sh build test
receipt_count=$(sh infra/compose.sh exec -T db psql -U postgres -d mingjing -Atc 'SELECT count(*) FROM receipts')
test "$receipt_count" = 0
printf '%s\n' 'Independent Compose project started with zero receipts and a new namespace.'
sh infra/compose.sh run --rm --no-deps -T test python -m pytest -q tests/test_smoke.py tests/test_at11_at12.py::test_at12_internal_network_and_database_permissions
