#!/bin/sh
# Build the firmware catalog. The catalog is the set of
# recipes-images/iotbench-*.bb recipes; MACHINES selects the architectures.
#   MACHINES  space-separated list (default: qemuarm64)
#             e.g. MACHINES="qemuarm64 qemuarm qemux86-64 qemux86 qemumips"
set -eu

cd "$(dirname -- "$0")/.."
MACHINES="${MACHINES:-qemuarm64}"

for machine in ${MACHINES}; do
    for bb in meta-iotbench/recipes-images/iotbench-*.bb; do
        firmware=$(basename "$bb" .bb)
        firmware=${firmware#iotbench-}
        echo "=== Building ${firmware} for ${machine} ==="
        YOCTO_MACHINE="$machine" FIRMWARE="$firmware" docker compose run --rm yocto
    done
done

echo "All firmwares built. See deploy-images/<firmware>/<machine>/."
