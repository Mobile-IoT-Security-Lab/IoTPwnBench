#!/bin/sh
# Boot the exported qemuarm64 firmware with QEMU on the host.
# Requires qemu-system-aarch64 and zstd.
#   QEMU_HTTP_PORT  host port forwarded to guest port 80 (default: 8080)
#   QEMU_ACCEL      tcg (default), or hvf on Apple Silicon together with QEMU_CPU=host
#   QEMU_CPU        emulated CPU (default: cortex-a57)
set -eu

DEPLOY_DIR="$(dirname -- "$0")/../deploy-images/qemuarm64"
ROOTFS="${DEPLOY_DIR}/router-dashboard-image-qemuarm64.rootfs.ext4"
HTTP_PORT="${QEMU_HTTP_PORT:-8080}"

# Decompress on first boot or after a new export. The ext4 image is not a
# snapshot, so dashboard settings survive reboots until the next export.
if [ ! -f "${ROOTFS}" ] || [ "${ROOTFS}.zst" -nt "${ROOTFS}" ]; then
    zstd -f -d "${ROOTFS}.zst" -o "${ROOTFS}"
fi

echo "Dashboard: http://127.0.0.1:${HTTP_PORT} (quit with Ctrl-A, then X)"

exec qemu-system-aarch64 \
    -machine "virt,accel=${QEMU_ACCEL:-tcg}" \
    -cpu "${QEMU_CPU:-cortex-a57}" \
    -smp 4 \
    -m 256 \
    -kernel "${DEPLOY_DIR}/Image" \
    -append "root=/dev/vda rw mem=256M ip=dhcp console=ttyAMA0 swiotlb=0" \
    -drive "id=disk0,file=${ROOTFS},if=none,format=raw" \
    -device virtio-blk-pci,drive=disk0 \
    -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:${HTTP_PORT}-:80" \
    -device virtio-net-pci,netdev=net0 \
    -object rng-random,filename=/dev/urandom,id=rng0 \
    -device virtio-rng-pci,rng=rng0 \
    -nographic
