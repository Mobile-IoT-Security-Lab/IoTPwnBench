#!/bin/sh
# Boot an exported IoTBench firmware with QEMU on the host.
# Requires the matching qemu-system-* binary and zstd.
#   FIRMWARE        firmware id under deploy-images/ (default: router-cwe078-os-command-injection)
#   YOCTO_MACHINE   qemuarm64 (default) | qemuarm | qemux86-64 | qemux86 | qemumips
#   QEMU_HTTP_PORT  host port forwarded to guest port 80 (default: 8080)
#   QEMU_ACCEL      tcg (default), or kvm/hvf where host and guest arch match
#   QEMU_CPU        override the emulated CPU
#   QEMU_PERSIST    1 keeps guest writes in the .ext4 across boots (power off the
#                   guest cleanly). Default 0 boots a throwaway overlay (-snapshot):
#                   the rootfs is always writable and the golden image never
#                   corrupts, but writes are dropped when QEMU exits.
set -eu

FIRMWARE="${FIRMWARE:-router-cwe078-os-command-injection}"
MACHINE="${YOCTO_MACHINE:-qemuarm64}"
IMAGE="iotbench-${FIRMWARE}"
DEPLOY_DIR="$(dirname -- "$0")/../deploy-images/${FIRMWARE}/${MACHINE}"
ROOTFS="${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4"
HTTP_PORT="${QEMU_HTTP_PORT:-8080}"
SMP=4

# Per-architecture QEMU parameters.
case "${MACHINE}" in
    qemuarm64)  QBIN=qemu-system-aarch64; QMACH=virt;  QCPU="${QEMU_CPU:-cortex-a57}"; KERNEL=Image;   CONSOLE=ttyAMA0; APPEND_EXTRA="swiotlb=0" ;;
    qemuarm)    QBIN=qemu-system-arm;     QMACH=virt;  QCPU="${QEMU_CPU:-cortex-a15}"; KERNEL=zImage;  CONSOLE=ttyAMA0; APPEND_EXTRA="" ;;
    qemux86-64) QBIN=qemu-system-x86_64;  QMACH=q35;   QCPU="${QEMU_CPU:-}";           KERNEL=bzImage; CONSOLE=ttyS0;   APPEND_EXTRA="" ;;
    qemux86)    QBIN=qemu-system-i386;    QMACH=pc;    QCPU="${QEMU_CPU:-}";           KERNEL=bzImage; CONSOLE=ttyS0;   APPEND_EXTRA="" ;;
    qemumips)   QBIN=qemu-system-mips;    QMACH=malta; QCPU="${QEMU_CPU:-}";           KERNEL=vmlinux; CONSOLE=ttyS0;   APPEND_EXTRA=""; SMP=1 ;;
    *) echo "Unsupported YOCTO_MACHINE: ${MACHINE}" >&2; exit 1 ;;
esac

if [ ! -f "${ROOTFS}.zst" ]; then
    echo "Firmware not found: ${ROOTFS}.zst" >&2
    echo "Build it first, e.g. YOCTO_MACHINE=${MACHINE} FIRMWARE=${FIRMWARE} docker compose up yocto" >&2
    exit 1
fi

if [ "${QEMU_PERSIST:-0}" = "1" ]; then
    # Persist writes into the .ext4. Refresh it only from a newer export.
    SNAPSHOT=""
    if [ ! -f "${ROOTFS}" ] || [ "${ROOTFS}.zst" -nt "${ROOTFS}" ]; then
        zstd -f -d "${ROOTFS}.zst" -o "${ROOTFS}"
    fi
else
    # Always start from a clean base; QEMU writes go to a discarded overlay.
    SNAPSHOT="-snapshot"
    zstd -f -d "${ROOTFS}.zst" -o "${ROOTFS}"
fi

CPU_ARG=""
[ -n "${QCPU}" ] && CPU_ARG="-cpu ${QCPU}"

echo "Firmware: ${FIRMWARE} (${MACHINE})"
echo "Dashboard: http://127.0.0.1:${HTTP_PORT} (quit with Ctrl-A, then X)"

# shellcheck disable=SC2086
exec "${QBIN}" \
    -machine "${QMACH},accel=${QEMU_ACCEL:-tcg}" \
    ${CPU_ARG} \
    -smp "${SMP}" \
    -m 256 \
    ${SNAPSHOT} \
    -kernel "${DEPLOY_DIR}/${KERNEL}" \
    -append "root=/dev/vda rw console=${CONSOLE} ip=dhcp ${APPEND_EXTRA}" \
    -drive "id=disk0,file=${ROOTFS},if=none,format=raw" \
    -device virtio-blk-pci,drive=disk0 \
    -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:${HTTP_PORT}-:80" \
    -device virtio-net-pci,netdev=net0 \
    -object rng-random,filename=/dev/urandom,id=rng0 \
    -device virtio-rng-pci,rng=rng0 \
    -nographic
