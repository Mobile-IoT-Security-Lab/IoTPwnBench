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

inherit core-image

# Leave enough room for PHP and for settings written by the dashboard.
IMAGE_ROOTFS_SIZE = "131072"
IMAGE_ROOTFS_EXTRA_SPACE = "32768"
