SUMMARY = "Bootable QEMU router dashboard image"
DESCRIPTION = "Minimal ARM64 image with Lighttpd, PHP CGI and the RouterOS web simulator"
LICENSE = "MIT"

IMAGE_INSTALL = "packagegroup-core-boot \
                 lighttpd \
                 lighttpd-module-cgi \
                 php-cgi \
                 router-dashboard \
                 ${CORE_IMAGE_EXTRA_INSTALL}"

IMAGE_LINGUAS = " "

inherit core-image extrausers

# Serial console credentials for this demo image.
# The plain-text password never reaches the filesystem: only its SHA-512 crypt
# hash is stored here.
ROOT_PASSWORD_HASH = "\$6\$yoctorouter\$3Bf/vJsZadvtkzaq9UWC2Vl9Ua/xfjnfn9NhnpJaPWdF3B4nVmWsVz4SwtVQasmtiY45f7aU0UWvPWBcrrrau."
EXTRA_USERS_PARAMS = "usermod -p '${ROOT_PASSWORD_HASH}' root;"

# Leave enough room for PHP and for settings written by the dashboard.
IMAGE_ROOTFS_SIZE = "131072"
IMAGE_ROOTFS_EXTRA_SPACE = "32768"
