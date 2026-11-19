#!/bin/sh
set -eu
umask 077
mkdir -p .p1
[ ! -e .p1/runtime.env ] || { echo 'Use the existing isolated run or a fresh checkout.' >&2; exit 1; }
printf 'MINGJING_RUN_ID=%s\n' "local-$(openssl rand -hex 4)" > .p1/runtime.env
printf 'TEMPORAL_NAMESPACE=%s\n' "p1-$(openssl rand -hex 4)" >> .p1/runtime.env
for name in P1_BOOTSTRAP_PASSWORD P1_TEMPORAL_PASSWORD P1_DB_PASSWORD; do
    printf '%s=%s\n' "$name" "$(openssl rand -hex 24)" >> .p1/runtime.env
done
