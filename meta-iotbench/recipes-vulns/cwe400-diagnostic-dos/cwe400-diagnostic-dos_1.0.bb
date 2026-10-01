SUMMARY = "IoTBench vulnerability module - CWE-400 uncontrolled resource consumption"
DESCRIPTION = "Builds a diagnostic helper that allocates attacker-selected memory. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://iotbench-dos.c"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-dos.c -o ${B}/iotbench-dos
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-dos ${D}${bindir}/iotbench-dos
    install -d ${D}${datadir}/router-dashboard/modules/diagnostic-dos
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/diagnostic-dos/module.php
}

FILES:${PN} = "${bindir}/iotbench-dos ${datadir}/router-dashboard/modules/diagnostic-dos"
