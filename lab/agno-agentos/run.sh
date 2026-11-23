#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$LAB_OUT"
stage=$(mktemp -d)
p=$(openssl rand -hex 20)
w=$(openssl rand -hex 20)
echo "::add-mask::$p"
echo "::add-mask::$w"
image=docker.io/library/postgres@sha256:e80acae3f1109e8e4533618b594918936f2858c63afc7204c4773148a673add8
product_container="agno-product-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
witness_container="agno-witness-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
trap 'docker rm -f "$product_container" "$witness_container" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$product_container" -p 127.0.0.1:15432:5432 -e POSTGRES_PASSWORD="$p" "$image"
docker run -d --name "$witness_container" -p 127.0.0.1:15433:5432 -e POSTGRES_PASSWORD="$w" "$image"
python3 -m venv "$stage/venv"
"$stage/venv/bin/pip" -q install --report "$stage/packages.json" -r lab/agno-agentos/requirements.lock
"$stage/venv/bin/pip" freeze > "$LAB_OUT/versions.txt"
"$stage/venv/bin/python" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({r["metadata"]["name"]:r["download_info"]["archive_info"]["hashes"] for r in d["install"]},sort_keys=True,indent=2))' "$stage/packages.json" > "$LAB_OUT/wheel-hashes.json"
cat "$LAB_OUT/versions.txt"
export PRODUCT_DSN="postgresql://postgres:$p@127.0.0.1:15432/postgres"
export WITNESS_DSN="postgresql://postgres:$w@127.0.0.1:15433/postgres"
cd lab/agno-agentos
"$stage/venv/bin/python" -u trial.py
# Preserve the same decoded synthetic records in the repository after artifact expiry.
"$stage/venv/bin/python" - "$LAB_OUT" <<'PY'
import base64, hashlib, io, os, pathlib, sys, zipfile
root = pathlib.Path(sys.argv[1])
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix in {".txt", ".json", ".jsonl"}:
            bundle.writestr(path.name, path.read_bytes())
data = buffer.getvalue()
print("AGNO_ARCHIVE_SHA256", hashlib.sha256(data).hexdigest())
encoded = base64.b64encode(data).decode("ascii")
for offset in range(0, len(encoded), 2000):
    print("AGNO_ARCHIVE_PART", offset, encoded[offset:offset + 2000])
PY
