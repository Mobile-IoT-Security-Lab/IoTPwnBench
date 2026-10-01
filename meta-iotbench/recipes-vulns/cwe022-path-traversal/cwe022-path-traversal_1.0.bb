SUMMARY = "IoTBench vulnerability module - CWE-22 path traversal"
DESCRIPTION = "Adds a report reader that concatenates a filename into a filesystem path. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://status.txt"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${localstatedir}/lib/router-dashboard/reports
    install -m 0644 ${S}/status.txt ${D}${localstatedir}/lib/router-dashboard/reports/status.txt
    install -d ${D}${datadir}/router-dashboard/modules/path-traversal
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/path-traversal/module.php
}

FILES:${PN} = "${localstatedir}/lib/router-dashboard/reports ${datadir}/router-dashboard/modules/path-traversal"
