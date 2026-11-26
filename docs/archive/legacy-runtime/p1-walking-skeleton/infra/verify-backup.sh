#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
mkdir -p .p1
database=p1_mingjing_restore
db_command() { sh infra/compose.sh exec -T db "$@"; }
summary() {
    db_command psql -U postgres -d "$1" -v ON_ERROR_STOP=1 -Atc "
        SELECT 'receipts=' || count(*) || ', sha256=' ||
          encode(sha256(convert_to(coalesce(string_agg(result::text, E'\\n' ORDER BY operation_id), ''), 'UTF8')), 'hex')
          FROM receipts;
        SELECT 'markers=' || count(*) FROM markers;
        SELECT 'audit=' || count(*) FROM audit;
        SELECT 'approvals=' || count(*) FROM approvals;
    "
}
summary mingjing > .p1/source.summary
grep -Eq '^receipts=[1-9][0-9]*,' .p1/source.summary
db_command pg_dump -U postgres --format=custom --dbname=mingjing > .p1/mingjing.dump
db_command createdb -U postgres "$database"
trap 'db_command dropdb -U postgres "$database"' EXIT
db_command pg_restore -U postgres --exit-on-error --dbname="$database" < .p1/mingjing.dump
summary "$database" > .p1/restore.summary
cmp .p1/source.summary .p1/restore.summary
printf '%s\n' 'PostgreSQL custom format backup and fresh database restore matched.'
cat .p1/restore.summary
