#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
namespace=$(sed -n 's/^TEMPORAL_NAMESPACE=//p' .p1/runtime.env)
workflow_id=$(python3 -c '
import json
with open(".p1/results/AT01.json") as stream:
    rows = json.load(stream)["shared_contract"]
print(next(item["result"]["workflow_id"] for item in rows if item["kind"] == "agent"))
')
history() {
    sh infra/compose.sh run --rm --no-deps -T --entrypoint temporal namespace workflow show \
        --namespace "$namespace" --workflow-id "$workflow_id" --output json
}
history > .p1/history.before.json
sh infra/compose.sh restart temporal >&2
sh infra/compose.sh up -d --wait temporal >&2
history > .p1/history.after.json
cmp .p1/history.before.json .p1/history.after.json
printf 'History retained across a Temporal Server restart for %s\n' "$workflow_id"
sha256sum .p1/history.after.json
