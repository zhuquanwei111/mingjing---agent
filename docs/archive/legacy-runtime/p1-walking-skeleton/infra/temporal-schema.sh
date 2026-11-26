#!/bin/sh
set -eu
for database in temporal temporal_visibility; do
    directory=temporal
    if [ "$database" = temporal_visibility ]; then directory=visibility; fi
    temporal-sql-tool --plugin postgres12 --ep db -p 5432 -u p1_temporal --db "$database" setup-schema -v 0.0
    temporal-sql-tool --plugin postgres12 --ep db -p 5432 -u p1_temporal --db "$database" update-schema \
        -d "/etc/temporal/schema/postgresql/v12/$directory/versioned"
done
