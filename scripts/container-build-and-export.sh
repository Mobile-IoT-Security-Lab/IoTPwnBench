#!/bin/bash
# Build router-dashboard-image and copy the files needed by run-qemu.sh to /export.
set -eo pipefail

IMAGE=router-dashboard-image

source /opt/yocto/yocto-env.sh
bitbake "${IMAGE}"

DEPLOY_DIR="${BUILDDIR}/tmp/deploy/images/${MACHINE}"
KERNEL=$(sed -n 's/^kernel_imagetype = //p' "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.qemuboot.conf")

mkdir -p "/export/${MACHINE}"
cp -L "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4.zst" "${DEPLOY_DIR}/${KERNEL}" "/export/${MACHINE}/"
echo "Firmware exported to deploy-images/${MACHINE}"
