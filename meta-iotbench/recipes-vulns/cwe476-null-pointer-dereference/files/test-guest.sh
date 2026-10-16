#!/bin/sh
# Regression harness only; the vulnerability is in fixture-device-info.c.
set -eu
ulimit -c 0
helper='@BINDIR@/fixture-device-info'
data='@DATADIR@/iotbench/null-pointer-dereference'
device=${1:?Expected synthetic device class}
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
[ "$(dd if="$helper" bs=4 count=1 2>/dev/null)" = "$(printf '\177ELF')" ]
printf '%s\n' 'PASS native ELF, device identity and ordinary permissions'

lookup() {
    setpriv --reuid=65534 --regid=65534 --clear-groups \
        "$data/test-null-dereference" --run "$@"
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
public='Record ID: 1
Record Value: SYNTHETIC_PUBLIC_FIXTURE_DATA'
status='Record ID: 2
Record Value: SYNTHETIC_STATUS_FIXTURE_DATA'
check 0 "$public" public
check 0 "$public" public
check 0 "$status" status
printf '%s\n' 'PASS valid public and status records, deterministic output and exit zero'

check 2 ''
check 2 '' public extra
printf '%s\n' 'PASS argument count validated before argv[1] access'

# The supervisor checks si_addr and si_code while the kernel stops the child,
# then forwards its original SIGSEGV and verifies actual signal termination.
diagnostic=$(setpriv --reuid=65534 --regid=65534 --clear-groups \
    "$data/test-null-dereference")
[ "$diagnostic" = 'NULL_DEREFERENCE_CONFIRMED signal=SIGSEGV address=0 code=SEGV_MAPERR' ]
printf '%s\n' "PASS missing-record: $diagnostic"

[ "$(setpriv --reuid=65534 --regid=65534 --clear-groups id -u)" = 65534 ]
[ "$(ulimit -c)" = 0 ]
printf '%s\n' 'PASS unprivileged subprocess, watchdog and disabled core dumps'
