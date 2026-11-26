#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
results=$(mktemp -d .p1/smoke.XXXXXXXX)
printf 'Smoke results: %s/%s\n' "$PWD" "$results"
smoke_port=$(.venv/bin/python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
smoke_address="127.0.0.1:$smoke_port"
.p1/bin/temporal server start-dev --ip 127.0.0.1 --port "$smoke_port" --headless --db-filename "$results/temporal.sqlite" > "$results/cli-server.log" 2>&1 &
smoke_pid=$!
trap 'kill "$smoke_pid" 2>/dev/null || :; wait "$smoke_pid" 2>/dev/null || :' EXIT
for attempt in {1..30}; do
    if .p1/bin/temporal operator cluster health --address "$smoke_address" > "$results/health-check.txt" 2>&1; then
        break
    fi
    kill -0 "$smoke_pid"
    sleep 1
done
.p1/bin/temporal operator cluster health --address "$smoke_address"
env -i PATH="$PATH" TEMPORAL_ADDRESS="$smoke_address" PYTHONPATH="$PWD/src" \
    LANGGRAPH_STRICT_MSGPACK=true LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false OTEL_TRACES_EXPORTER=none \
    .venv/bin/python -m pytest -q -s --junitxml="$results/smoke.junit.xml" tests/test_smoke.py | tee "$results/smoke.log"
