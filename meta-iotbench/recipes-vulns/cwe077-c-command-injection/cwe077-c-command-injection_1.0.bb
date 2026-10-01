SUMMARY = "IoTBench vulnerability module - CWE-77 C command injection"
DESCRIPTION = "Builds a C helper that passes unsanitized input to system(). Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://iotbench-cdiag.c"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-cdiag.c -o ${B}/iotbench-cdiag
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-cdiag ${D}${bindir}/iotbench-cdiag
    install -d ${D}${datadir}/router-dashboard/modules/c-injection
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/c-injection/module.php
}

FILES:${PN} = "${bindir}/iotbench-cdiag ${datadir}/router-dashboard/modules/c-injection"
