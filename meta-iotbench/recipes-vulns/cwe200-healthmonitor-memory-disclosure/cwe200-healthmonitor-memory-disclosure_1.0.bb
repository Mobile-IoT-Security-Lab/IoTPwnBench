SUMMARY = "IoTBench health monitor memory disclosure"
DESCRIPTION = "A patient-monitor service returns attacker-selected device-memory ranges without authentication. Inspired by CVE-2018-10599; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-healthd.c file://iotbench-healthd.service"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-healthd.service"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-healthd.c -o ${B}/iotbench-healthd
}

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${B}/iotbench-healthd ${D}${sbindir}/iotbench-healthd
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-healthd.service ${D}${systemd_system_unitdir}/iotbench-healthd.service
}

FILES:${PN} = "${sbindir}/iotbench-healthd ${systemd_system_unitdir}/iotbench-healthd.service"
