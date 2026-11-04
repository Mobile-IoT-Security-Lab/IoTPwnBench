#!/bin/sh
# Fixed-state Apache startup for manual terminal interaction inside isolate.
# Request input is supplied separately by the researcher through curl.
set -eu

[ "$#" -eq 0 ] || {
    echo "manual Apache server accepts no arguments" >&2
    exit 2
}
[ "$(id -u)" = 1000 ] || {
    echo "manual Apache server requires the isolated unprivileged identity" >&2
    exit 1
}
[ "$(cat /run/iotbench-apache-isolated)" = "fixture-v1" ] || {
    echo "manual Apache server requires the isolation marker" >&2
    exit 1
}

rm -f /state/settings.db /state/sessions.db /state/records.db
mkdir -p /state/allowed
printf 'synthetic-public\n' > /state/allowed/public.txt
printf 'synthetic-traversal-sentinel\n' > /state/sentinel.txt

/usr/bin/sqlite3 /state/settings.db <<'SQL'
CREATE TABLE settings (name TEXT PRIMARY KEY, value TEXT);
INSERT INTO settings VALUES ('benchmark', 'initial');
SQL
/usr/bin/sqlite3 /state/sessions.db <<'SQL'
CREATE TABLE sessions (sid TEXT PRIMARY KEY, identity TEXT, role TEXT, csrf TEXT);
SQL
/usr/bin/sqlite3 /state/records.db <<'SQL'
CREATE TABLE records (name TEXT, label TEXT, designated INTEGER);
INSERT INTO records VALUES ('public', 'synthetic-public-record', 0);
INSERT INTO records VALUES ('sentinel', 'synthetic-sql-sentinel', 1);
SQL

CWE=$(sed -n 's/.*"cwe":"\([0-9][0-9][0-9]\)".*/\1/p' /fixture/variant.json)
[ -n "$CWE" ] || {
    echo "manual Apache server cannot identify its installed variant" >&2
    exit 1
}
printf 'manual-apache-ready variant=CWE-%s uid=%s\n' "$CWE" "$(id -u)" >&2
exec /usr/sbin/httpd -f /fixture/httpd.conf -DFOREGROUND
