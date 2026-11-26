#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .p1/results
run_id=$(sed -n 's/^MINGJING_RUN_ID=//p' .p1/runtime.env)
suffix=$(openssl rand -hex 3)
runner="mingjing-p1-$run_id-evidence-$suffix"
sh infra/compose.sh up -d --wait temporal
sh infra/compose.sh run --rm --no-deps namespace
sh infra/compose.sh build test
result=0
sh infra/compose.sh run --name "$runner" --no-deps -T test > .p1/results/acceptance.log 2>&1 || result=$?
cat .p1/results/acceptance.log
sudo docker cp "$runner:/evidence/." .p1/results/
sudo docker rm "$runner" >/dev/null
exit "$result"
