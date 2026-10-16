#!/bin/sh
# Local regression only; helper invocations run without root in a disposable guest.
set -eu
helper='@BINDIR@/fixture-db-query'
data='@DATADIR@/iotbench/c-sql-injection'
db="$data/fixture.db"
device=${1:?Expected synthetic device class}
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
[ "$(stat -c '%u:%g:%a' "$db")" = '0:0:444' ]
[ "$(dd if="$helper" bs=4 count=1 2>/dev/null)" = "$(printf '\177ELF')" ]
[ "$(dd if="$db" bs=15 count=1 2>/dev/null)" = 'SQLite format 3' ]
before=$(md5sum "$db")
printf '%s\n' 'PASS native ELF, packaged SQLite database, device identity and ordinary permissions'

lookup() {
    # The serial login is the existing lab root; the vulnerable binary needs no privileges.
    setpriv --reuid=65534 --regid=65534 --clear-groups "$helper" "$@"
}
check() {
    expected_exit=$1
    expected_output=$2
    shift 2
    actual_exit=0
    output=$(lookup "$@") || actual_exit=$?
    [ "$actual_exit" -eq "$expected_exit" ]
    [ "$output" = "$expected_output" ]
}
public='public|SYNTHETIC_PUBLIC_FIXTURE_DATA'
both="$public
internal|SYNTHETIC_INTERNAL_FIXTURE_DATA"
check 0 "$public" public
check 0 "$public" public
check 0 '' unknown
check 0 '' ''
printf '%s\n' 'PASS normal lookup returns only the public synthetic record, deterministically'

check 0 "$both" "public' OR '1'='1"
check 0 "$both" "public' OR '1'='1"
printf '%s\n' 'PASS SQL injection changes SELECT logic and returns the synthetic internal record'

check 2 ''
check 2 '' public extra
long_input=$(printf '%0240d' 0)
check 0 '' "$long_input"
check 2 '' "${long_input}0"
check 1 '' "'"
check 0 '' '$(printf harmless); ../synthetic-only'
printf '%s\n' 'PASS argument counts, 240-byte boundary, malformed SQL and literal shell-shaped value'

# Only benign SELECT payloads; no write/delete/schema-change test statements.
check 1 '' "public'; SELECT record_value FROM fixture_records; --"
check 1 '' "public' UNION SELECT name, sql FROM sqlite_master --"
check 1 '' "public' UNION SELECT 'fixture', sqlite_version() --"
printf '%s\n' 'PASS extra statements, non-fixture tables and SQL functions rejected independently of WHERE logic'

[ "$(setpriv --reuid=65534 --regid=65534 --clear-groups id -u)" = 65534 ]
[ "$before" = "$(md5sum "$db")" ]
[ ! -e "$db-journal" ] && [ ! -e "$db-wal" ] && [ ! -e "$db-shm" ]
printf '%s\n' 'PASS unprivileged execution, unchanged database bytes and no journal sidecars'
