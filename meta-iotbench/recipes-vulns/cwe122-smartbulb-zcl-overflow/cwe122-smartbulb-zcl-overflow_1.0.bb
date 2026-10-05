SUMMARY = "IoTBench smart bulb ZCL heap overflow"
DESCRIPTION = "A Zigbee commissioning bridge trusts a ZCL string length larger than its heap field. Inspired by CVE-2020-6007; the radio transport is represented by TCP for QEMU. Intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-zcld.c file://iotbench-zcld.service"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-zcld.service"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-zcld.c -o ${B}/iotbench-zcld
}

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${B}/iotbench-zcld ${D}${sbindir}/iotbench-zcld
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-zcld.service ${D}${systemd_system_unitdir}/iotbench-zcld.service
}

FILES:${PN} = "${sbindir}/iotbench-zcld ${systemd_system_unitdir}/iotbench-zcld.service"
