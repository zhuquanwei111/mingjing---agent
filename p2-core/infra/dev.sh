#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
action=${1:-}
env_file=${P2_ENV_FILE:-.runtime/dev.env}
if [ ! -e "$env_file" ]; then
    [ "$action" != clean ] || exit 0
    [ "$action" = init ] || { echo 'Run sh p2-core/infra/dev.sh init first.' >&2; exit 1; }
    umask 077
    mkdir -p "$(dirname "$env_file")"
    printf 'P2_PROJECT=mingjing-p2-%s\n' "$(openssl rand -hex 5)" > "$env_file"
    for key in P2_BOOTSTRAP_PASSWORD P2_MIGRATION_PASSWORD P2_APP_PASSWORD P2_TEMPORAL_PASSWORD; do
        printf '%s=%s\n' "$key" "$(openssl rand -hex 24)" >> "$env_file"
    done
fi
project=$(sed -n 's/^P2_PROJECT=//p' "$env_file")
printf '%s\n' "$project" | grep -Eq '^mingjing-p2-[0-9a-f]{10}$'
compose() {
    docker compose --env-file "$env_file" -p "$project" -f infra/compose.yaml "$@"
}
prepare() {
    compose build test
    compose up -d --wait db temporal
    compose run --rm --no-deps -T namespace
    compose run --rm --no-deps -T migrate
}
case "$action" in
    init)
        prepare
        ;;
    test)
        compose build test
        runner="$project-test-$(openssl rand -hex 4)"
        trap 'docker rm "$runner" >/dev/null 2>&1 || :' EXIT
        status=0
        compose run --no-deps -T --name "$runner" test || status=$?
        docker cp "$runner:/evidence/junit.xml" "$(dirname "$env_file")/junit.xml"
        exit "$status"
        ;;
    run)
        prepare
        compose up -d --no-deps api worker
        ;;
    status)
        compose ps -a
        ;;
    stop)
        compose down
        ;;
    clean)
        compose down --volumes --remove-orphans
        rm "$env_file"
        ;;
    *)
        echo 'usage: sh infra/dev.sh init|test|run|status|stop|clean' >&2
        exit 2
        ;;
esac
