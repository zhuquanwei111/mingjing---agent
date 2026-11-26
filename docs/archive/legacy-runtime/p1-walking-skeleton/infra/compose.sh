#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
run_id=$(sed -n 's/^MINGJING_RUN_ID=//p' .p1/runtime.env)
case "$run_id" in local-[0-9a-f]*) ;; *) echo 'Invalid isolated run ID' >&2; exit 1 ;; esac
if [ "$(id -u)" -eq 0 ]; then
    exec docker compose --env-file .p1/runtime.env -p "mingjing-p1-$run_id" -f infra/compose.yaml "$@"
fi
exec sudo docker compose --env-file .p1/runtime.env -p "mingjing-p1-$run_id" -f infra/compose.yaml "$@"
