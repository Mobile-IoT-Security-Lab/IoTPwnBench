SUMMARY = "IoTBench Modbus project-apply command injection"
DESCRIPTION = "A vendor-style Modbus maintenance register bank passes a staged PLC project name to a shell command. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=f5b1129dfbfc8afc083db247ff942d07"

SRC_URI = "file://LICENSE \
           file://iotbench-modbus-maintenance.c \
           file://iotbench-modbusd-vulnerable.conf"
S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "iotbench-modbusd"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-modbus-maintenance.c \
        -o ${B}/iotbench-modbus-maintenance
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-modbus-maintenance ${D}${bindir}/iotbench-modbus-maintenance

    install -d ${D}${systemd_system_unitdir}/iotbench-modbusd.service.d
    install -m 0644 ${S}/iotbench-modbusd-vulnerable.conf \
        ${D}${systemd_system_unitdir}/iotbench-modbusd.service.d/10-vulnerable-maintenance.conf
}

FILES:${PN} = "${bindir}/iotbench-modbus-maintenance \
               ${systemd_system_unitdir}/iotbench-modbusd.service.d"
