#!/bin/sh
# Smoke checks on the actual cross-built ELF; optional --asan checks diagnostics.
set -eu
ulimit -c 0
helper='@BINDIR@/fixture-buffer-write'
data='@DATADIR@/iotbench/native-buffer-overflow'
device=${1:?Expected synthetic device class}
case "${2:-}" in
    ''|--asan) ;;
    *) echo 'Expected optional --asan' >&2; exit 2 ;;
esac
[ "$#" -le 2 ]
work=$(mktemp -d /tmp/iotbench-buffer.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
chmod 0755 "$work"
cd "$work"
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
[ "$(dd if="$helper" bs=4 count=1 2>/dev/null)" = "$(printf '\177ELF')" ]
grep -F 'CWE-787' "$data/ground-truth.json" >/dev/null
printf '%s\n' 'PASS device identity, ELF, primary CWE and ordinary permissions'

run() {
    if command -v timeout >/dev/null 2>&1; then
        timeout 15 setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs "$helper" "$@"
    else
        setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs "$helper" "$@"
    fi
}
[ "$(printf '\000\000' | run)" = 'OK 0 0' ]
[ "$(printf '\000\001A' | run)" = 'OK 1 65' ]
output=$({ printf '\000\100'; printf '%064d' 0; } | run)
[ "$output" = 'OK 64 3072' ]
printf '%s\n' 'PASS empty, single-byte and exact 64-byte capacity inputs as UID/GID 65534'

reject() {
    status=0
    output=$(run "$@") || status=$?
    [ "$status" -eq 2 ] && [ -z "$output" ]
}
printf '' | reject
printf '\000' | reject
printf '\000\002A' | reject
printf '\000\001AB' | reject
printf '\000\001\000' | reject
printf '\000\001\177' | reject
printf '\001\001' | reject
printf '\377\377' | reject
printf '\000\000' | reject extra
printf '%s\n' 'PASS truncated, surplus, nonprintable, over-transport and extra-argument inputs rejected'
if [ "${2:-}" = --asan ]; then
    helper="$helper-asan"
    [ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
    export ASAN_OPTIONS='detect_leaks=0:halt_on_error=1:abort_on_error=0:symbolize=1:exitcode=86'
    [ "$(printf '\000\000' | run)" = 'OK 0 0' ]
    [ "$(printf '\000\001A' | run)" = 'OK 1 65' ]
    output=$({ printf '\000\100'; printf '%064d' 0; } | run)
    [ "$output" = 'OK 64 3072' ]
    status=0
    { printf '\000\101'; printf '%065d' 0; } | run >result.out 2>asan.log || status=$?
    [ "$status" -eq 86 ] && [ ! -s result.out ]
    grep -F 'ERROR: AddressSanitizer: global-buffer-overflow' asan.log
    grep -F 'WRITE of size 1' asan.log
    grep -F 'configuration' asan.log >/dev/null
    sink=$(sed -n 's/ *"sink_line": \([0-9]*\),/\1/p' "$data/ground-truth.json")
    grep -F "fixture-buffer-write.c:$sink" asan.log
    printf '%s\n' 'PASS ASan reports the intended store in a separate unprivileged process'
fi
printf '%s\n' 'PASS guest checks; normal ELF is never given oversized valid input'
