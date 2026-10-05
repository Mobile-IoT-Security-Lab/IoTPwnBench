SUMMARY = "IoTBench PLC Modbus project-loader stack overflow"
DESCRIPTION = "A vendor-specific Modbus function permits a project chunk larger than its stack destination. Inspired by parser flaws such as CVE-2018-20818; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-modbus-overflow.c file://iotbench-modbusd-overflow.conf"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "iotbench-modbusd"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -fno-stack-protector ${S}/iotbench-modbus-overflow.c -o ${B}/iotbench-modbus-overflow
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-modbus-overflow ${D}${bindir}/iotbench-modbus-overflow
    install -d ${D}${systemd_system_unitdir}/iotbench-modbusd.service.d
    install -m 0644 ${S}/iotbench-modbusd-overflow.conf ${D}${systemd_system_unitdir}/iotbench-modbusd.service.d/10-stack-overflow.conf
}

FILES:${PN} = "${bindir}/iotbench-modbus-overflow ${systemd_system_unitdir}/iotbench-modbusd.service.d"
