SUMMARY = "IoTBench vulnerability module - CWE-276 leaked private key"
DESCRIPTION = "Installs a private key in the web document root with world-readable permissions. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://device-private.key"

S = "${UNPACKDIR}"

do_install() {
    install -d ${D}/www/pages/debug
    install -m 0644 ${S}/device-private.key ${D}/www/pages/debug/device-private.key
}

FILES:${PN} = "/www/pages/debug/device-private.key"
