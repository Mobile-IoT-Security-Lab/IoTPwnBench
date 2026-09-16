#!/bin/sh
set -eu

CONTAINER_NAME="${CONTAINER_NAME:-yocto}"
MACHINE="${YOCTO_MACHINE:-qemuarm64}"
IMAGE_NAME="router-dashboard-image"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
DEST_DIR="${PROJECT_DIR}/deploy-images/${MACHINE}"
DEPLOY_DIR="/workdir/yocto-firmware/build/tmp/deploy/images/${MACHINE}"

case "${MACHINE}" in
    ''|*[!A-Za-z0-9._+-]*)
        echo "YOCTO_MACHINE non valido: ${MACHINE}" >&2
        exit 1
        ;;
esac

if [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)" != "true" ]; then
    echo "Il container ${CONTAINER_NAME} non è in esecuzione." >&2
    exit 1
fi

mkdir -p "${DEST_DIR}"

container_path() {
    docker exec "${CONTAINER_NAME}" readlink -f "${DEPLOY_DIR}/$1"
}

ROOTFS_SOURCE=$(container_path "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst")
QEMUBOOT_SOURCE=$(container_path "${IMAGE_NAME}-${MACHINE}.rootfs.qemuboot.conf")
MANIFEST_SOURCE=$(container_path "${IMAGE_NAME}-${MACHINE}.rootfs.manifest")
KERNEL_FILE=$(docker exec "${CONTAINER_NAME}" sed -n 's/^kernel_imagetype = //p' "${QEMUBOOT_SOURCE}")
case "${KERNEL_FILE}" in
    ''|*/*|*[!A-Za-z0-9._+-]*)
        echo "kernel_imagetype non valido in ${QEMUBOOT_SOURCE}: ${KERNEL_FILE}" >&2
        exit 1
        ;;
esac
KERNEL_SOURCE=$(container_path "${KERNEL_FILE}")

docker cp "${CONTAINER_NAME}:${ROOTFS_SOURCE}" "${DEST_DIR}/${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst"
docker cp "${CONTAINER_NAME}:${KERNEL_SOURCE}" "${DEST_DIR}/${KERNEL_FILE}"
docker cp "${CONTAINER_NAME}:${QEMUBOOT_SOURCE}" "${DEST_DIR}/${IMAGE_NAME}-${MACHINE}.rootfs.qemuboot.conf"
docker cp "${CONTAINER_NAME}:${MANIFEST_SOURCE}" "${DEST_DIR}/${IMAGE_NAME}-${MACHINE}.rootfs.manifest"

# Non rimuovere l'ext4 locale: QEMU potrebbe averlo aperto. run-qemu.sh lo
# rigenera dal nuovo file compresso al successivo avvio usando questo marker.
touch "${DEST_DIR}/.${IMAGE_NAME}-${MACHINE}.rootfs.refresh"

if command -v shasum >/dev/null 2>&1; then
    (
        cd "${DEST_DIR}"
        shasum -a 256 \
            "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst" \
            "${KERNEL_FILE}" \
            "${IMAGE_NAME}-${MACHINE}.rootfs.qemuboot.conf" \
            "${IMAGE_NAME}-${MACHINE}.rootfs.manifest" > SHA256SUMS
    )
elif command -v sha256sum >/dev/null 2>&1; then
    (
        cd "${DEST_DIR}"
        sha256sum \
            "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst" \
            "${KERNEL_FILE}" \
            "${IMAGE_NAME}-${MACHINE}.rootfs.qemuboot.conf" \
            "${IMAGE_NAME}-${MACHINE}.rootfs.manifest" > SHA256SUMS
    )
fi

echo "Firmware esportato in ${DEST_DIR}"
ls -lh "${DEST_DIR}"
