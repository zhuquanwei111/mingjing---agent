#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out=/tmp/wmn-evidence
mkdir -p "$out"
trap 'for c in wmn-server wmn-worker wmn-replacement; do if docker inspect "$c" >/dev/null 2>&1; then docker logs "$c" >"$out/$c.log" 2>&1; fi; done' EXIT
windmill_repo=ghcr.io/windmill-labs/windmill
if docker pull "$windmill_repo:1.882.0" >"$out/image.txt" 2>&1; then
  ce_tag="$windmill_repo:1.882.0"
else
  cat "$out/image.txt"
  ce_tag="$windmill_repo:v1.882.0"
  docker pull "$ce_tag" | tee -a "$out/image.txt"
fi
ce=$(docker image inspect "$ce_tag" --format '{{index .RepoDigests 0}}')
docker image inspect "$ce" --format '{{json .Config.Labels}}' | tee "$out/image-labels.json"
echo "$ce" | tee "$out/ce-digest.txt"
pg=docker.io/library/postgres@sha256:526f86d93c6ea08fd3f1fe5605650cacc781b2c6013169a0ad8f42c7d3d84f32
docker run -d --name wmn-pg --network host -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=windmill "$pg" -c listen_addresses=127.0.0.1
for i in {1..60}; do docker exec wmn-pg pg_isready -U postgres >/dev/null && break; sleep 1; done
export DATABASE_URL=postgres://postgres@127.0.0.1:5432/windmill?sslmode=disable
export BASE_URL=http://127.0.0.1:8000
# Only the synthetic, loopback model endpoint is allowed. No real model credentials.
export ALLOW_PRIVATE_AI_BASE_URLS=127.0.0.1
docker run -d --network host --name wmn-server -e DATABASE_URL -e BASE_URL -e MODE=server -e ALLOW_PRIVATE_AI_BASE_URLS "$ce"
for i in {1..150}; do curl -fsS "$BASE_URL/api/version" >"$out/version.txt" 2>/dev/null && break; sleep 1; done
cat "$out/version.txt"
grep -F '1.882.0' "$out/version.txt"
if [[ "${1:-}" == "--preflight" || ! -f harness.py ]]; then exit 0; fi
export CE_DIGEST="$ce"
python3 -u harness.py
