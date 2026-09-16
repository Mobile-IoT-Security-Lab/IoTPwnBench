#!/bin/sh
set -eu

CONTAINER_NAME="${CONTAINER_NAME:-yocto}"
MACHINE="${YOCTO_MACHINE:-qemuarm64}"
META_OPENEMBEDDED_REV="14282a02be9c74a1276a7cda7d6c89e054699a11"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
FIRMWARE_DIR="/workdir/yocto-firmware"

case "${MACHINE}" in
    ''|*[!A-Za-z0-9._+-]*)
        echo "YOCTO_MACHINE non valido: ${MACHINE}" >&2
        exit 1
        ;;
esac

if ! docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    echo "Container ${CONTAINER_NAME} non trovato." >&2
    exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}")" != "true" ]; then
    docker start "${CONTAINER_NAME}" >/dev/null
fi

docker exec "${CONTAINER_NAME}" sh -lc "
    set -eu
    cd '${FIRMWARE_DIR}/layers'
    if [ ! -d meta-openembedded/.git ]; then
        git clone --branch wrynose https://git.openembedded.org/meta-openembedded
    fi
    if ! git -C meta-openembedded checkout '${META_OPENEMBEDDED_REV}'; then
        if [ \"\$(git -C meta-openembedded rev-parse --is-shallow-repository)\" = true ]; then
            git -C meta-openembedded fetch --unshallow origin wrynose
        else
            git -C meta-openembedded fetch origin wrynose
        fi
        git -C meta-openembedded checkout '${META_OPENEMBEDDED_REV}'
    fi
"

if docker inspect -f '{{range .Mounts}}{{println .Destination}}{{end}}' "${CONTAINER_NAME}" | \
    grep -Fxq "${FIRMWARE_DIR}/layers/meta-router-dashboard"; then
    echo "Layer meta-router-dashboard già mappato dalla repository locale."
else
    docker cp "${PROJECT_DIR}/meta-router-dashboard" "${CONTAINER_NAME}:${FIRMWARE_DIR}/layers/"
fi

docker exec "${CONTAINER_NAME}" bash -lc "
    set -e
    cd '${FIRMWARE_DIR}'
    source layers/openembedded-core/oe-init-build-env build >/dev/null
    sed -i '/^[[:space:]]*MACHINE[[:space:]]*=/d' conf/local.conf
    printf '\nMACHINE = \"%s\"\n' '${MACHINE}' >> conf/local.conf
    bitbake-layers show-layers | grep -F '${FIRMWARE_DIR}/layers/meta-openembedded/meta-oe' >/dev/null || \
        bitbake-layers add-layer '${FIRMWARE_DIR}/layers/meta-openembedded/meta-oe'
    bitbake-layers show-layers | grep -F '${FIRMWARE_DIR}/layers/meta-router-dashboard' >/dev/null || \
        bitbake-layers add-layer '${FIRMWARE_DIR}/layers/meta-router-dashboard'
    bitbake router-dashboard-image
"

docker exec "${CONTAINER_NAME}" sh -lc "
    find '${FIRMWARE_DIR}/build/tmp/deploy/images/${MACHINE}' -maxdepth 1 \
        \( -name 'router-dashboard-image-*.rootfs.ext4*' -o -name 'router-dashboard-image-*.qemuboot.conf' \) \
        -printf '%TY-%Tm-%Td %TH:%TM  %10s  %f\n' | sort
"

YOCTO_MACHINE="${MACHINE}" "${SCRIPT_DIR}/export-firmware.sh"
