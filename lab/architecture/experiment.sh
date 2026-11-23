source "$fixture/model.sh"
export LAB_ROUTE="$route" LAB_NS="$P2_PROJECT" LAB_REV="$GITHUB_SHA"
export LAB_APP_DSN="postgresql://$P2_PROJECT:$MJLAB_DB_PASSWORD@db/$P2_PROJECT"
witness_role="${P2_PROJECT}_w"
witness_pw=$(openssl rand -hex 20)
export LAB_WITNESS_DSN="postgresql://$witness_role:$witness_pw@db/$witness_role"
export LAB_TOKEN=$(openssl rand -hex 30) LAB_ADMIN_TOKEN=$(openssl rand -hex 30)
dc exec -T db psql -U postgres -v ON_ERROR_STOP=1 -v who="$witness_role" -v pass="$witness_pw" <<'SQL'
CREATE ROLE :"who" LOGIN PASSWORD :'pass';
CREATE DATABASE :"who" OWNER :"who";
REVOKE CONNECT ON DATABASE :"who" FROM PUBLIC;
SQL
opts=(-e LAB_ROUTE -e LAB_NS -e LAB_REV -e LAB_APP_DSN -e LAB_WITNESS_DSN -e LAB_TOKEN -e LAB_ADMIN_TOKEN -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONUNBUFFERED=1)
mounts=()
for f in ports.py shared_input.py witness.py worker.py suite.py plugin_fixture.py; do mounts+=(-v "$fixture/$f:/lab/$f:ro"); done
mounts+=(-v "$fixture/$route:/lab/$route:ro")
if [[ "$route" = a ]]; then
  dc run --rm -T --no-deps migrate
  dc run --rm -T --no-deps "${opts[@]}" "${mounts[@]}" -e PYTHONPATH=/lab:/mingjing/src test python /lab/suite.py
else
  docker build -t "$P2_PROJECT-independent" "$fixture/b"
  docker run --rm "$P2_PROJECT-independent" python -c 'import json;print("INSTALL_LOCK",json.dumps([(i["metadata"]["name"],i["metadata"]["version"],i["download_info"]["archive_info"]["hashes"]["sha256"]) for i in json.load(open("/opt/installed.json"))["install"]]))'
  docker run --rm --network "${P2_PROJECT}_default" "${opts[@]}" "${mounts[@]}" -e PYTHONPATH=/lab "$P2_PROJECT-independent" python /lab/suite.py
fi

