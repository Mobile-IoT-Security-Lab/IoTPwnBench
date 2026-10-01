SUMMARY = "IoTBench vulnerability module - CWE-89 SQL injection in HTTP auth"
DESCRIPTION = "Adds a vulnerable login panel that concatenates credentials into a SQL query. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard sqlite3"

do_install() {
    install -d ${D}${datadir}/router-dashboard/modules/sqli-auth
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/sqli-auth/module.php
}

FILES:${PN} = "${datadir}/router-dashboard/modules/sqli-auth"
