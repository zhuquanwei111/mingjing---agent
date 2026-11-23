#!/usr/bin/env bash
set -euo pipefail
net="gate-$(openssl rand -hex 8)"
db="$net-db"
image="$net-fixture"
pass=$(openssl rand -hex 24)
pg="docker.io/library/postgres@sha256:e80acae3f1109e8e4533618b594918936f2858c63afc7204c4773148a673add8"
cleanup() {
  docker rm -fv "$db" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
  docker image rm "$image" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker build -q -t "$image" lab/architecture/b
docker network create --internal "$net"
docker run -d --rm --name "$db" --network "$net" -e "POSTGRES_PASSWORD=$pass" "$pg"
for ((i=0;i<60;i++)); do
  if docker exec "$db" pg_isready -h 127.0.0.1 -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$db" pg_isready -h 127.0.0.1 -U postgres
docker exec -i "$db" psql -U postgres -v ON_ERROR_STOP=1 -v pass="$pass" <<'SQL'
CREATE ROLE gate LOGIN PASSWORD :'pass';
CREATE DATABASE gate OWNER gate;
SQL
git rev-parse HEAD
sha256sum lab/architecture/b/linux-amd64.lock lab/handoff/PLAN.md
docker run --rm --network "$net" --cap-drop ALL --security-opt no-new-privileges \
  -v "$PWD/lab/handoff:/exp:ro" -e "LAB_DSN=postgresql://gate:$pass@$db/gate" "$image" python /exp/probe.py
