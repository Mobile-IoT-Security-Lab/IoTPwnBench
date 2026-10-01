SUMMARY = "IoTBench vulnerability module - CWE-416 use after free"
DESCRIPTION = "Builds a C helper that reuses a freed authorization object. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://iotbench-uaf.c"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-uaf.c -o ${B}/iotbench-uaf
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-uaf ${D}${bindir}/iotbench-uaf
    install -d ${D}${datadir}/router-dashboard/modules/uaf
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/uaf/module.php
}

FILES:${PN} = "${bindir}/iotbench-uaf ${datadir}/router-dashboard/modules/uaf"
