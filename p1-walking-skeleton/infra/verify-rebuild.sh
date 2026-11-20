#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
root=$(mktemp -d /tmp/mingjing-p1-rebuild.XXXXXX)
project_started=0
run_id=
finish() {
    original_status=$?
    trap - EXIT
    if [ "$project_started" -eq 1 ]; then
        current_run_id=$(sed -n 's/^MINGJING_RUN_ID=//p' "$root/.p1/runtime.env" 2>/dev/null) || current_run_id=
        if [ "$current_run_id" != "$run_id" ]; then
            printf 'Rebuild run identity changed; refusing cleanup. Retained recovery directory: %s\n' "$root" >&2
            [ "$original_status" -ne 0 ] || original_status=1
            exit "$original_status"
        fi
        if ! sh "$root/infra/compose.sh" down --volumes; then
            printf 'Rebuild cleanup failed. Retained recovery directory and credentials: %s\n' "$root" >&2
            printf 'Retry cleanup with: sh "%s/infra/compose.sh" down --volumes\n' "$root" >&2
            [ "$original_status" -ne 0 ] || original_status=1
            exit "$original_status"
        fi
    fi
    if ! rm -rf "$root"; then
        printf 'Could not remove owned rebuild directory: %s\n' "$root" >&2
        [ "$original_status" -ne 0 ] || original_status=1
    fi
    exit "$original_status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cp -R .dockerignore infra requirements src tests "$root/"
cd "$root"
sh infra/new-run.sh
run_id=$(sed -n 's/^MINGJING_RUN_ID=//p' .p1/runtime.env)
printf '%s\n' "$run_id" | grep -Eq '^local-[0-9a-f]{8}$'
# An interrupted or failed first up may already have created project resources.
project_started=1
sh infra/compose.sh up -d --wait temporal
sh infra/compose.sh run --rm --no-deps namespace
sh infra/compose.sh build test
receipt_count=$(sh infra/compose.sh exec -T db psql -U postgres -d mingjing -Atc 'SELECT count(*) FROM receipts')
test "$receipt_count" = 0
printf '%s\n' 'Independent Compose project started with zero receipts and a new namespace.'
sh infra/compose.sh run --rm --no-deps -T test python -m pytest -q tests/test_smoke.py tests/test_at11_at12.py::test_at12_internal_network_and_database_permissions
