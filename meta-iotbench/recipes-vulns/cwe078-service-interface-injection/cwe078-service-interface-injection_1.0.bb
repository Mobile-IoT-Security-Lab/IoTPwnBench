SUMMARY = "IoTBench vulnerability module - CWE-78 service interface command injection"
DESCRIPTION = "Runs a TCP service interface that passes unsanitized commands to a shell. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-service-iface.c file://iotbench-service-iface.service"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-service-iface.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-service-iface.c -o ${B}/iotbench-service-iface
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-service-iface ${D}${bindir}/iotbench-service-iface
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-service-iface.service ${D}${systemd_system_unitdir}/iotbench-service-iface.service
}

FILES:${PN} = "${bindir}/iotbench-service-iface ${systemd_system_unitdir}/iotbench-service-iface.service"
