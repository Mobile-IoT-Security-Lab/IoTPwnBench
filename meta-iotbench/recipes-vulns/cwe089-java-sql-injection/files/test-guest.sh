#!/bin/sh
# Test harness only: the vulnerable SQL construction/execution is in Java.
set -eu
data='@DATADIR@/iotbench/java-sql-injection'
jar="$data/fixture-db-query.jar"
db="$data/fixture.db"
device=${1:?Expected synthetic device class}
grep -Fx "DEVICE_CLASS=\"$device\"" /etc/iotbench/device.conf >/dev/null
[ "$(stat -c '%u:%g:%a' "$jar")" = '0:0:644' ]
[ "$(stat -c '%u:%g:%a' "$db")" = '0:0:444' ]
[ -r '@DATADIR@/java/iotbench-sqlite-jdbc.jar' ]
[ -r '@LIBDIR@/libsqlitejdbc.so' ]
before=$(md5sum "$db")
printf '%s\n' 'PASS Java JAR, JDBC dependency, synthetic database and device identity'

lookup() {
    setpriv --reuid=65534 --regid=65534 --clear-groups \
        java -Xms8m -Xmx32m -XX:+UseSerialGC -XX:-UsePerfData -jar "$jar" "$@"
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
printf '%s\n' 'PASS ordinary lookup returns only the public synthetic record'

check 0 "$both" "public' OR '1'='1"
check 0 "$both" "public' OR '1'='1"
printf '%s\n' 'PASS Java JDBC SQL injection returns the additional synthetic internal record'

check 2 ''
check 2 '' public extra
check 2 '' ''
long_input=$(printf '%0240d' 0)
check 0 '' "$long_input"
check 2 '' "${long_input}0"
check 1 '' "'"
check 0 '' '$(printf harmless); ../synthetic-only'
printf '%s\n' 'PASS argument counts, length boundary, SQL error and literal shell-shaped input'

[ "$(setpriv --reuid=65534 --regid=65534 --clear-groups id -u)" = 65534 ]
[ "$before" = "$(md5sum "$db")" ]
[ ! -e "$db-journal" ] && [ ! -e "$db-wal" ] && [ ! -e "$db-shm" ]
printf '%s\n' 'PASS unprivileged execution and unchanged read-only database without journal sidecars'
