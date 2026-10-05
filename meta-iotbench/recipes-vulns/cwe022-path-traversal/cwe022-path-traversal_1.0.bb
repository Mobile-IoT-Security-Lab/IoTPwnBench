SUMMARY = "IoTBench Lighttpd fallback - CWE-22 path traversal"
DESCRIPTION = "Adds a global Lighttpd 404 dispatcher with unsafe double URL decoding. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://path-dispatch.php file://lighttpd-path-traversal.conf"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}/www/pages/.iotbench
    install -m 0644 ${S}/path-dispatch.php ${D}/www/pages/.iotbench/path-dispatch.php
    install -d ${D}${sysconfdir}/lighttpd/conf.d
    install -m 0644 ${S}/lighttpd-path-traversal.conf ${D}${sysconfdir}/lighttpd/conf.d/90-iotbench-path-traversal.conf
}

FILES:${PN} = "/www/pages/.iotbench/path-dispatch.php ${sysconfdir}/lighttpd/conf.d/90-iotbench-path-traversal.conf"
