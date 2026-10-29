#!/bin/bash
# Prepare the export bind mount, then run the builder without root privileges.
set -euo pipefail
if [[ $(id -u) != 0 ]]; then
    exec "$@"
fi
[[ -d /export ]] || { echo "/export must be mounted" >&2; exit 1; }
export_gid=$(stat -c %g /export)
# Preserve host ownership; inherit the host group on new export directories.
chmod g+ws /export
umask 0002
export HOME="$(getent passwd yocto | cut -d: -f6)"
export USER=yocto LOGNAME=yocto
# Check writability with the actual build identity before invoking BitBake.
setpriv --reuid=yocto --regid=yocto --groups="$export_gid" -- bash -euc '
    probe=$(mktemp /export/.write-check.XXXXXX)
    rm -f "$probe"
'
exec setpriv --reuid=yocto --regid=yocto --groups="$export_gid" -- "$@"
