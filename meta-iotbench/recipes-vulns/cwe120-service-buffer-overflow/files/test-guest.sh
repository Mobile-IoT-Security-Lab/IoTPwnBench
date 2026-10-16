#!/bin/sh
set -eu
data=/usr/share/iotbench/service-buffer-overflow
device=${1:?device profile required}
grep -Fx "DEVICE_CLASS=\"$device\"" /etc/iotbench/device.conf >/dev/null
test "$(stat -c '%u:%g:%a' /usr/bin/fixture-label-service)" = '0:0:755'
ulimit -c 0
trap 'systemctl stop iotbench-label.service' EXIT
systemctl reset-failed iotbench-label.service
systemctl start iotbench-label.service
for attempt in 1 2 3 4 5; do
    test ! -S /run/iotbench-label/service.sock || break
    sleep 1
done
setpriv --reuid=65534 --regid=65534 --clear-groups \
    python3 "$data/test-service.py" --request /run/iotbench-label/service.sock
systemctl stop iotbench-label.service
# A cgroup limits resident memory without breaking ASan's shadow-memory mapping.
systemd-run --quiet --wait --pipe --collect -p User=nobody -p Group=nogroup \
    -p MemoryMax=256M -p TasksMax=16 -p RuntimeMaxSec=60 -p LimitCORE=0 \
    -p NoNewPrivileges=yes -p PrivateNetwork=yes -p RestrictAddressFamilies=AF_UNIX \
    python3 "$data/test-service.py"
