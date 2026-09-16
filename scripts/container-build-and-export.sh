#!/bin/bash
set -eo pipefail

FIRMWARE_DIR="/workdir/yocto-firmware"
MACHINE="${YOCTO_MACHINE:-qemuarm64}"
IMAGE_NAME="router-dashboard-image"
META_OPENEMBEDDED_REV="14282a02be9c74a1276a7cda7d6c89e054699a11"
DEPLOY_DIR="${FIRMWARE_DIR}/build/tmp/deploy/images/${MACHINE}"
EXPORT_DIR="/export/${MACHINE}"

case "${MACHINE}" in
    ''|*[!A-Za-z0-9._+-]*)
        echo "YOCTO_MACHINE non valido: ${MACHINE}" >&2
        exit 1
        ;;
esac

if [[ ! -f "${FIRMWARE_DIR}/layers/openembedded-core/oe-init-build-env" ]]; then
    echo "Ambiente Yocto non trovato in ${FIRMWARE_DIR}. Ricrea il builder con docker compose up --build." >&2
    exit 1
fi

echo "Sincronizzazione dipendenze Yocto..."
cd "${FIRMWARE_DIR}/layers"
if [[ ! -d meta-openembedded/.git ]]; then
    git clone --branch wrynose https://git.openembedded.org/meta-openembedded
fi
if ! git -C meta-openembedded checkout "${META_OPENEMBEDDED_REV}"; then
    if [[ "$(git -C meta-openembedded rev-parse --is-shallow-repository)" == "true" ]]; then
        git -C meta-openembedded fetch --unshallow origin wrynose
    else
        git -C meta-openembedded fetch origin wrynose
    fi
    git -C meta-openembedded checkout "${META_OPENEMBEDDED_REV}"
fi

echo "Build ${IMAGE_NAME} per ${MACHINE}..."
cd "${FIRMWARE_DIR}"
source layers/openembedded-core/oe-init-build-env build >/dev/null
sed -i '/^[[:space:]]*MACHINE[[:space:]]*=/d' conf/local.conf
printf '\nMACHINE = "%s"\n' "${MACHINE}" >> conf/local.conf

echo "Build base core-image-minimal per ${MACHINE}..."
bitbake core-image-minimal

bitbake-layers show-layers | grep -F "${FIRMWARE_DIR}/layers/meta-openembedded/meta-oe" >/dev/null || \
    bitbake-layers add-layer "${FIRMWARE_DIR}/layers/meta-openembedded/meta-oe"
bitbake-layers show-layers | grep -F "${FIRMWARE_DIR}/layers/meta-router-dashboard" >/dev/null || \
    bitbake-layers add-layer "${FIRMWARE_DIR}/layers/meta-router-dashboard"
echo "Build dashboard ${IMAGE_NAME} per ${MACHINE}..."
bitbake "${IMAGE_NAME}"

echo "Esportazione firmware nella cartella locale deploy-images/${MACHINE}..."
mkdir -p "${EXPORT_DIR}"

QEMUBOOT_NAME="${IMAGE_NAME}-${MACHINE}.rootfs.qemuboot.conf"
QEMUBOOT_PATH=$(readlink -f "${DEPLOY_DIR}/${QEMUBOOT_NAME}")
if [[ ! -f "${QEMUBOOT_PATH}" ]]; then
    echo "Configurazione QEMU mancante: ${DEPLOY_DIR}/${QEMUBOOT_NAME}" >&2
    exit 1
fi

KERNEL_FILE=$(sed -n 's/^kernel_imagetype = //p' "${QEMUBOOT_PATH}")
case "${KERNEL_FILE}" in
    ''|*/*|*[!A-Za-z0-9._+-]*)
        echo "kernel_imagetype non valido in ${QEMUBOOT_PATH}: ${KERNEL_FILE}" >&2
        exit 1
        ;;
esac

copy_artifact() {
    local source_name="$1"
    local destination_name="$2"
    local source_path

    source_path=$(readlink -f "${DEPLOY_DIR}/${source_name}")
    if [[ ! -f "${source_path}" ]]; then
        echo "Artefatto Yocto mancante: ${DEPLOY_DIR}/${source_name}" >&2
        exit 1
    fi
    cp -Lf "${source_path}" "${EXPORT_DIR}/${destination_name}"
}

copy_artifact "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst" "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst"
copy_artifact "${KERNEL_FILE}" "${KERNEL_FILE}"
copy_artifact "${QEMUBOOT_NAME}" "${QEMUBOOT_NAME}"
copy_artifact "${IMAGE_NAME}-${MACHINE}.rootfs.manifest" "${IMAGE_NAME}-${MACHINE}.rootfs.manifest"

# Non rimuovere l'ext4 locale: QEMU potrebbe averlo aperto. run-qemu.sh lo
# rigenera dal nuovo file compresso al successivo avvio usando questo marker.
touch "${EXPORT_DIR}/.${IMAGE_NAME}-${MACHINE}.rootfs.refresh"

(
    cd "${EXPORT_DIR}"
    sha256sum \
        "${IMAGE_NAME}-${MACHINE}.rootfs.ext4.zst" \
        "${KERNEL_FILE}" \
        "${QEMUBOOT_NAME}" \
        "${IMAGE_NAME}-${MACHINE}.rootfs.manifest" > SHA256SUMS
)

echo "Firmware pronto sul computer host in deploy-images/${MACHINE}."
echo "QEMU resta locale: eseguire ./scripts/run-qemu.sh fuori dal container."
ls -lh "${EXPORT_DIR}"

# Mantiene disponibile il builder per docker exec e per gli script manuali.
exec /bin/bash
