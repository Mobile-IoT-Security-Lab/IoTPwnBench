#!/bin/sh
# Explicit local regression; every helper invocation runs without privileges.
set -eu
helper='@BINDIR@/fixture-batch-size'
data='@DATADIR@/iotbench/integer-overflow'
device=${1:?Expected synthetic device class}
grep -Fx "DEVICE_CLASS=\"$device\"" '@SYSCONFDIR@/iotbench/device.conf' >/dev/null
[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ]
[ "$(dd if="$helper" bs=4 count=1 2>/dev/null)" = "$(printf '\177ELF')" ]
grep -F 'CWE-190' "$data/ground-truth.json" >/dev/null
printf '%s\n' 'PASS native ELF, correct device profile, ground truth and ordinary permissions'

calculate() {
    setpriv --reuid=65534 --regid=65534 --clear-groups "$helper" "$@"
}
check() {
    count=$1
    total=$2
    decision=$3
    output=$(calculate "$count")
    # Decimal aliases (leading zeroes) are checked separately below.
    expected="record_count = $count
record_size = 1024
total_size = $total
max_capacity = 4096
Synthetic batch $decision"
    [ "$output" = "$expected" ]
}
check 2 2048 accepted
check 2 2048 accepted
normal=$(calculate 2)
[ "$(calculate 0002)" = "$normal" ]
printf '%s\n' 'PASS normal input 2 gives total 2048 and accepted, repeatedly'

check 4194304 4294967296 'exceeds capacity'
check 4194304 4294967296 'exceeds capacity'
printf '%s\n' 'PASS overflow input 4194304: total 4294967296 does not wrap and the batch exceeds capacity'

check 0 0 accepted
check 4 4096 accepted
check 5 5120 'exceeds capacity'
check 4194303 4294966272 'exceeds capacity'
check 4194305 4294968320 'exceeds capacity'
check 4294967295 4398046510080 'exceeds capacity'
printf '%s\n' 'PASS capacity boundary, adjacent counts and UINT32_MAX are all computed without wrap'

reject() {
    status=0
    output=$(calculate "$@") || status=$?
    [ "$status" -eq 2 ] && [ -z "$output" ]
}
reject
reject 2 extra
for invalid in '' -1 +2 ' 2' '2 ' '2
' 2x 1.5 0x2 4294967296 18446744073709551616 '$(printf harmless); ../fixture'; do
    reject "$invalid"
done
printf '%s\n' 'PASS malformed, signed, out-of-range and wrong-count arguments rejected with exit 2'

[ "$(setpriv --reuid=65534 --regid=65534 --clear-groups id -u)" = 65534 ]
printf '%s\n' 'PASS all numerical checks terminate normally as UID/GID 65534 with no privileged helper'
