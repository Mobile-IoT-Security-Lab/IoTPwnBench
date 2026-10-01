SUMMARY = "IoTBench vulnerability module - CWE-276 leaked private key"
DESCRIPTION = "Installs a private key in the web document root with world-readable permissions. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://device-private.key"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${datadir}/router-dashboard/modules/leaked-key
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/leaked-key/module.php

    install -d ${D}/www/pages/debug
    install -m 0644 ${S}/device-private.key ${D}/www/pages/debug/device-private.key
}

FILES:${PN} = "${datadir}/router-dashboard/modules/leaked-key /www/pages/debug/device-private.key"
