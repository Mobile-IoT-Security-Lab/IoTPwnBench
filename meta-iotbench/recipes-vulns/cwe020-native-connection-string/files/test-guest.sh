#!/bin/sh
# Run from the disposable guest serial console. The helper itself never uses a shell.
set -eu
helper='@BINDIR@/fixture-connection'
data='@DATADIR@/iotbench/native-connection-string'
device=${1:?Expected synthetic device class}
[ "$#" -eq 1 ]
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
grep -F 'CWE-20' "$data/ground-truth.json" >/dev/null
work=$(mktemp -d /tmp/iotbench-connection-guest.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cd "$work"
run() {
    timeout 15 setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs "$helper"
}
check() {
    expected=$1
    actual=$(run)
    [ "$actual" = "OK readonly=$expected marker=SYNTHETIC_CONNECTION_RESOURCE" ]
}
printf '\000\007private' | check 1
printf '\000\006shared' | check 1
printf '\000\017private&mode=rw#' | check 0
printf '\000\007private' | check 1
printf '%s\n' 'PASS real SQLite normal, injected and reset connection modes'
reject() {
    expected=$1
    status=0
    actual=$(run 2>error) || status=$?
    [ "$status" -eq "$expected" ] && [ -z "$actual" ]
    if [ "$expected" -eq 2 ]; then grep -Fx 'ERR INVALID' error >/dev/null;
    else grep -Fx 'ERR CONNECT' error >/dev/null; fi
}
printf '\000\000' | reject 3
printf '\000\003bad' | reject 3
printf '\000\003%%FF' | reject 2
printf '\000\010private' | reject 2
printf '\000\007privateX' | reject 2
printf '\001\001' | reject 2
# 256-byte well-formed URI value including an ignored synthetic padding key.
{ printf '\001\000private&padding='; printf '%0240d' 0; } | check 1
printf '%s\n' 'PASS empty, malformed, transport and boundary controls'
printf '%s\n' 'PASS all helpers ran as UID/GID 65534 with built-in local containment'
