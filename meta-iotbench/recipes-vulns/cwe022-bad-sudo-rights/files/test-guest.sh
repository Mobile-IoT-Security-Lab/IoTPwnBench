#!/bin/sh
# Root-console test harness only. The privileged reader never executes this.
# INTENTIONALLY INSECURE SYNTHETIC TEST FIXTURE — LOCAL SECURITY TESTING ONLY — NOT FOR DEPLOYMENT
set -eu

[ "$(id -u)" = 0 ] || { echo 'Run this test from the guest root console' >&2; exit 1; }
if [ "$#" -gt 0 ]; then
    grep -Fxq "DEVICE_CLASS=\"$1\"" /etc/iotbench/device.conf || {
        echo 'FAIL unexpected device profile' >&2; exit 1;
    }
fi
fixture_root='@FIXTURE_ROOT@'
helper='@BINDIR@/iotbench-maintenance-read'
sudo_bin='@BINDIR@/sudo'
cat_bin='@BASE_BINDIR@/cat'
signal='ROOT_ONLY_PATH_TRAVERSAL_CONFIRMED'

fail() { echo "FAIL $*" >&2; exit 1; }
as_fixture() { "$sudo_bin" -n -u fixturetest -- "$@"; }
read_fixture() { as_fixture "$sudo_bin" -n -- "$helper" "$@"; }
denied() {
    if "$@" >/dev/null 2>&1; then fail "unexpected success: $*"; fi
}

id_output=$(as_fixture id)
case "$id_output" in uid=994\(fixturetest\)*) ;; *) fail 'wrong non-privileged user';; esac
as_fixture "$cat_bin" "$fixture_root/data/status.conf" | grep -q 'MAINTENANCE_STATUS=ready'
denied as_fixture "$cat_bin" "$fixture_root/private/root-only.conf"
denied as_fixture "$helper" "$fixture_root/data/../private/root-only.conf"
echo 'PASS non-privileged user cannot directly read the private synthetic file'

result=$(read_fixture "$fixture_root/data/status.conf")
printf '%s\n' "$result" | grep -q '^READER_EUID=0$'
printf '%s\n' "$result" | grep -q '^MAINTENANCE_STATUS=ready$'
echo 'PASS sudo executes the specific reader as root for the intended data file'

for traversal in '../private/root-only.conf' './../private/root-only.conf'; do
    result=$(read_fixture "$fixture_root/data/$traversal")
    printf '%s\n' "$result" | grep -q '^READER_EUID=0$'
    printf '%s\n' "$result" | grep -q "=$signal\$"
done
echo 'PASS sudo-authorized traversal reads fake root-only data outside data/'

denied read_fixture "$fixture_root/private/root-only.conf"
denied as_fixture "$sudo_bin" -n -- "$cat_bin" "$fixture_root/private/root-only.conf"
denied read_fixture "$fixture_root/data/status.conf" extra
denied read_fixture "$fixture_root/data"
denied read_fixture "$fixture_root/data/."
denied read_fixture "$fixture_root/data/missing.conf"
denied read_fixture "$fixture_root/data/../../../../etc/passwd"
denied read_fixture "$fixture_root/data/status.conf;id"
echo 'PASS sudo scope, argument count, regular-file checks and synthetic containment'
echo 'PASS Bad SUDO Rights — Path Traversal (CWE-22)'
