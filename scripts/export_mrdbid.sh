#!/usr/bin/env bash
# Export the character tables from the old MRDBID MySQL database.
# Reads through the MySQL client only (never the data folder).
# Credentials come from ~/.my.cnf. Output goes to import_data/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")/.."
DB=mrdbid_development
HOST=127.0.0.1
PORT=3306
OUT=import_data
TABLES="source_data_types source_data parts observation_methods fungus_types display_options mr_characters lookup_items core_character_sequences"
mkdir -p "$OUT"
STAMP=$(date +%Y-%m-%d)

# 1. Archive: a plain .sql dump of the tables (read-only, consistent snapshot).
mysqldump -h "$HOST" -P "$PORT" --single-transaction --no-tablespaces \
  --default-character-set=utf8mb4 "$DB" $TABLES > "$OUT/mrdbid_characters_$STAMP.sql"

# 2. JSON per table for the Django import (one array per table).
for t in $TABLES; do
  cols=$(mysql -h "$HOST" -P "$PORT" -N -B -e \
    "select group_concat(concat('''', column_name, ''', \`', column_name, '\`') order by ordinal_position)
     from information_schema.columns where table_schema='$DB' and table_name='$t'")
  mysql -h "$HOST" -P "$PORT" --default-character-set=utf8mb4 -N -B -r -e \
    "set session group_concat_max_len = 1073741824;
     select coalesce(json_arrayagg(json_object($cols)), json_array()) from (select * from \`$t\` order by id) x" "$DB" \
    > "$OUT/$t.json"
  n=$(mysql -h "$HOST" -P "$PORT" -N -B -e "select count(*) from \`$t\`" "$DB")
  echo "$t: $n rows"
done
# 3. Next AUTO_INCREMENT value per table, so new IDs never reuse deleted MRDBID IDs.
in_list=$(printf "'%s'," $TABLES); in_list=${in_list%,}
mysql -h "$HOST" -P "$PORT" -N -B -r -e \
  "set session information_schema_stats_expiry = 0;
   select json_objectagg(table_name, auto_increment) from information_schema.tables
   where table_schema='$DB' and table_name in ($in_list)" > "$OUT/auto_increment.json"
echo "Wrote $OUT/"
