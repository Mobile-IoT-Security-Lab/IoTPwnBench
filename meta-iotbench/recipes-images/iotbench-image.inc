# Common IoTBench firmware image. Device-agnostic: a firmware requires this file
# plus one device profile (recipes-devices/<device>/device-<device>.inc) and
# installs one vulnerability package on top.
LICENSE = "MIT"

IMAGE_INSTALL = "packagegroup-core-boot \
                 iotbench-sim \
                 ${IOTBENCH_DEVICE_INSTALL} \
                 ${IOTBENCH_VULN_INSTALL} \
                 ${CORE_IMAGE_EXTRA_INSTALL}"

# Set by the device profile and the firmware recipe respectively.
IOTBENCH_DEVICE_INSTALL ?= ""
IOTBENCH_VULN_INSTALL ?= ""

IMAGE_LINGUAS = " "

inherit core-image extrausers

# Serial console credentials for these demo images.
# The plain-text password never reaches the filesystem: only its SHA-512 crypt
# hash is stored here.
ROOT_PASSWORD_HASH = "\$6\$yoctorouter\$3Bf/vJsZadvtkzaq9UWC2Vl9Ua/xfjnfn9NhnpJaPWdF3B4nVmWsVz4SwtVQasmtiY45f7aU0UWvPWBcrrrau."
EXTRA_USERS_PARAMS = "usermod -p '${ROOT_PASSWORD_HASH}' root;"

# Leave room for the device app and for state written at runtime.
IMAGE_ROOTFS_SIZE = "131072"
IMAGE_ROOTFS_EXTRA_SPACE = "32768"
