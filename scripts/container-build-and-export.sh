#!/bin/bash
# Build the selected IoTBench firmware and copy the files run-qemu.sh needs into
# /export/<firmware>/<machine>.
#   FIRMWARE  firmware id; builds iotbench-${FIRMWARE} (default: router-cwe078-os-command-injection)
set -eo pipefail

FIRMWARE="${FIRMWARE:-router-cwe078-os-command-injection}"
IMAGE="iotbench-${FIRMWARE}"

source /opt/yocto/yocto-env.sh
bitbake "${IMAGE}"

DEPLOY_DIR="${BUILDDIR}/tmp/deploy/images/${MACHINE}"
KERNEL=$(sed -n 's/^kernel_imagetype = //p' "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.qemuboot.conf")

EXPORT_DIR="/export/${FIRMWARE}/${MACHINE}"
mkdir -p "${EXPORT_DIR}"
cp -L "${DEPLOY_DIR}/${IMAGE}-${MACHINE}.rootfs.ext4.zst" "${DEPLOY_DIR}/${KERNEL}" "${EXPORT_DIR}/"
echo "Firmware exported to deploy-images/${FIRMWARE}/${MACHINE}"
