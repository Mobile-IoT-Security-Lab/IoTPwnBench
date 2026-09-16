#!/bin/sh
set -eu

MACHINE="qemuarm64"
IMAGE_NAME="router-dashboard-image"
QEMU_HTTP_PORT="${QEMU_HTTP_PORT:-8080}"
QEMU_BIN="${QEMU_BIN:-qemu-system-aarch64}"
QEMU_ACCEL="${QEMU_ACCEL:-tcg}"
QEMU_CPU="${QEMU_CPU:-cortex-a57}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
DEPLOY_DIR="${PROJECT_DIR}/deploy-images/${MACHINE}"
ROOTFS_ZST="${DEPLOY_DIR}/${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst"
ROOTFS_IMAGE="${DEPLOY_DIR}/${IMAGE_NAME}-${MACHINE}.rootfs.ext4"
ROOTFS_REFRESH="${DEPLOY_DIR}/.${IMAGE_NAME}-${MACHINE}.rootfs.refresh"
KERNEL_IMAGE="${DEPLOY_DIR}/Image"

case "${QEMU_HTTP_PORT}" in
    ''|*[!0-9]*) echo "QEMU_HTTP_PORT deve essere una porta numerica." >&2; exit 1 ;;
esac

if ! command -v "${QEMU_BIN}" >/dev/null 2>&1; then
    echo "${QEMU_BIN} non trovato. Installa QEMU sull'host locale." >&2
    exit 1
fi
if ! command -v zstd >/dev/null 2>&1; then
    echo "zstd non trovato. Installalo sull'host locale." >&2
    exit 1
fi
if [ ! -f "${ROOTFS_ZST}" ] || [ ! -f "${KERNEL_IMAGE}" ]; then
    echo "Firmware non esportato. Esegui prima ./scripts/export-firmware.sh." >&2
    exit 1
fi

if command -v pgrep >/dev/null 2>&1 && pgrep -f 'qemu-system-aarch64' >/dev/null 2>&1; then
    echo "QEMU ARM64 è già in esecuzione. Chiudi prima la sessione corrente con Ctrl-A, poi X." >&2
    exit 1
fi

if [ -f "${ROOTFS_REFRESH}" ] || [ ! -f "${ROOTFS_IMAGE}" ] || [ "${ROOTFS_ZST}" -nt "${ROOTFS_IMAGE}" ]; then
    echo "Decompressione del root filesystem..."
    zstd -f -d "${ROOTFS_ZST}" -o "${ROOTFS_IMAGE}"
    rm -f "${ROOTFS_REFRESH}"
fi

echo "Avvio QEMU locale (${QEMU_ACCEL}, CPU ${QEMU_CPU})"
echo "Dashboard: http://127.0.0.1:${QEMU_HTTP_PORT} (guest port 80)"
echo "Per uscire: Ctrl-A, poi X"

exec "${QEMU_BIN}" \
    -machine "virt,accel=${QEMU_ACCEL}" \
    -cpu "${QEMU_CPU}" \
    -smp 4 \
    -m 256 \
    -kernel "${KERNEL_IMAGE}" \
    -append "root=/dev/vda rw mem=256M ip=dhcp console=ttyAMA0 swiotlb=0" \
    -drive "id=disk0,file=${ROOTFS_IMAGE},if=none,format=raw" \
    -device virtio-blk-pci,drive=disk0 \
    -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:${QEMU_HTTP_PORT}-:80" \
    -device virtio-net-pci,netdev=net0 \
    -object rng-random,filename=/dev/urandom,id=rng0 \
    -device virtio-rng-pci,rng=rng0 \
    -nographic
