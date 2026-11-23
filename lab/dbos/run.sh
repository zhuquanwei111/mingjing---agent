#!/usr/bin/env bash
set -euo pipefail
LAB_DIR="$PWD/lab/dbos"
mkdir -p "$LAB_OUT"
[[ "$(git rev-parse HEAD)" == "$TEST_HEAD" ]]
pg_image=docker.io/library/postgres@sha256:e80acae3f1109e8e4533618b594918936f2858c63afc7204c4773148a673add8
tag="dbos-$(openssl rand -hex 6)"
password="$(openssl rand -hex 16)"
receiver_pass="$(openssl rand -hex 16)"
product_pass="$(openssl rand -hex 16)"
engine_pass="$(openssl rand -hex 16)"
db="$tag-product"
receiver="$tag-witness"
witness_pid=
cleanup() {
  status=$?
  if [[ -n "$witness_pid" ]]; then kill "$witness_pid" 2>/dev/null || true; fi
  REDACT_TEMP="$password $receiver_pass $product_pass $engine_pass" python3 - <<'PY2'
import os,pathlib
for f in pathlib.Path(os.environ['LAB_OUT']).glob('*.log'):
    content=f.read_text()
    for v in os.environ['REDACT_TEMP'].split():
        content=content.replace(v,'[redacted]')
    f.write_text(content)
PY2
  docker rm -fv "$db" "$receiver" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT
for hidden in "$password" "$receiver_pass" "$product_pass" "$engine_pass"; do echo "::add-mask::$hidden"; done
python3.12 -m venv /tmp/dbos-env
/tmp/dbos-env/bin/pip install -q --only-binary=:all: --require-hashes -r "$LAB_DIR/linux-cp312.lock"
/tmp/dbos-env/bin/pip check
export PATH="/tmp/dbos-env/bin:$PATH"
docker run -d --name "$db" -p 127.0.0.1::5432 -e POSTGRES_PASSWORD="$password" "$pg_image"
docker run -d --name "$receiver" -p 127.0.0.1::5432 -e POSTGRES_PASSWORD="$receiver_pass" -e POSTGRES_USER=witness "$pg_image"
for pg in "$db" "$receiver"; do
  for i in {1..60}; do
    if docker exec "$pg" pg_isready -h 127.0.0.1 >/dev/null 2>&1; then break; fi
    sleep 1
  done
done
docker exec -i "$db" psql -U postgres -v ON_ERROR_STOP=1 -v pp="$product_pass" -v ep="$engine_pass" <<'SQL'
CREATE ROLE product LOGIN PASSWORD :'pp';
CREATE ROLE engine LOGIN PASSWORD :'ep';
CREATE DATABASE product OWNER product;
CREATE DATABASE engine OWNER engine;
REVOKE CONNECT ON DATABASE engine,product FROM PUBLIC;
SQL
db_port="$(docker port "$db" 5432/tcp | cut -d: -f2)"
witness_port="$(docker port "$receiver" 5432/tcp | cut -d: -f2)"
export PRODUCT_DSN="postgresql://product:$product_pass@127.0.0.1:$db_port/product"
export ENGINE_DSN="postgresql://engine:$engine_pass@127.0.0.1:$db_port/engine"
export WITNESS_DSN="postgresql://witness:$receiver_pass@127.0.0.1:$witness_port/witness"
env -i PATH="$PATH" HOME="$HOME" WITNESS_DSN="$WITNESS_DSN" python -u "$LAB_DIR/witness.py" >"$LAB_OUT/witness.log" 2>&1 &
witness_pid=$!
for i in {1..40}; do
  if curl -fsS http://127.0.0.1:8080/ready >/dev/null 2>&1; then break; fi
  sleep .25
done
curl -fsS http://127.0.0.1:8080/ready
{
  uname -sm && python -VV && pip freeze
  docker exec "$db" psql -At -U postgres -c 'SHOW server_version'
  docker image inspect "$pg_image" --format '{{.Id}}'
  sha256sum "$LAB_DIR/linux-cp312.lock" "$LAB_DIR/witness.py"
} >"$LAB_OUT/versions.txt"
python - <<'PY'
import importlib.metadata as meta,json,os,pathlib
out={}
for lock in pathlib.Path('lab/dbos/linux-cp312.lock').read_text().splitlines():
    name=lock.split('==')[0]
    m=meta.metadata(name)
    out[name]={'version':m['Version'],'expression':m.get('License-Expression'), 'license':(m.get('License') or '')[:125],
               'classifiers':[v for v in m.get_all('Classifier',[]) if v.startswith('License ::')]}
pathlib.Path(os.environ['LAB_OUT'],'licenses.json').write_text(json.dumps(out,indent=2))
PY
python -u "$LAB_DIR/driver.py"
python -u "$LAB_DIR/takeover.py"
