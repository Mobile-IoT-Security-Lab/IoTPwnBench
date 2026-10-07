#!/bin/sh
# Explicit guest-root regression harness; the vulnerable helper never runs it.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run from the guest root console' >&2; exit 1; }
if [ "$#" -gt 0 ]; then
    grep -Fxq "DEVICE_CLASS=\"$1\"" /etc/iotbench/device.conf
fi
helper='@BINDIR@/iotbench-bash-read'
fixture_dir='@DATADIR@/iotbench/bash-path-traversal'
jail="$fixture_dir/rootfs"
fail() { echo "FAIL $*" >&2; exit 1; }
denied() { if "$helper" "$@" >/dev/null 2>&1; then fail "unexpected success: $*"; fi; }

result=$("$helper" public.txt)
printf '%s\n' "$result" | grep -Fxq 'SYNTHETIC_PUBLIC_FIXTURE_DATA'
echo 'PASS Bash helper reads the intended synthetic public file'

for input in '../internal/private-fixture.txt' './../internal/private-fixture.txt'; do
    result=$("$helper" "$input")
    printf '%s\n' "$result" | grep -Fxq 'SYNTHETIC_INTERNAL_FIXTURE_DATA'
done
echo 'PASS argument traversal escapes data/ and reads the synthetic internal file'

denied
denied public.txt extra
denied missing.txt
denied .
denied 'public.txt;printf COMMAND_INJECTION'
denied '$(printf COMMAND_INJECTION)'
denied '`printf COMMAND_INJECTION`'
denied 'public.txt *'
echo 'PASS invalid files and shell-shaped filenames do not execute commands'

# NOTICE exists in the guest outside the jail; its absence through traversal
# proves confinement without referring to any system secret or host file.
[ -f "$fixture_dir/NOTICE" ] || fail 'missing external fixture NOTICE'
denied '../NOTICE'
denied "../../../../../../../../$fixture_dir/NOTICE"
denied "../../../../../../../../$fixture_dir/rootfs$fixture_dir/data/public.txt"
result=$("$helper" "../../../../../../../../$fixture_dir/internal/private-fixture.txt")
printf '%s\n' "$result" | grep -Fxq 'SYNTHETIC_INTERNAL_FIXTURE_DATA'
[ "$(find "$jail" -type f | wc -l)" -eq 2 ] || fail 'jail must contain exactly two synthetic files'
[ -z "$(find "$jail" ! -type d ! -type f)" ] || fail 'unexpected symlink or special file in jail'
echo 'PASS deep traversal stays in the jail containing only synthetic fixture files'

[ "$(stat -c '%u:%g:%a' "$helper")" = '0:0:755' ] || fail 'unsafe helper permissions'
[ "$(stat -c '%u:%g:%a' '@LIBDIR@/iotbench/bash-path-traversal/fixture-confine.so')" = '0:0:755' ] || fail 'unsafe builtin permissions'
echo 'PASS Vulnerable Bash files — Path Traversal (CWE-22), without SUID or sudo'
