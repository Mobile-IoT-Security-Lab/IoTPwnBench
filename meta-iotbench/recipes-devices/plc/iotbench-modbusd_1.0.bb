SUMMARY = "IoTBench Modbus/TCP server (PLC device skeleton)"
DESCRIPTION = "Exposes simulated peripheral values as Modbus holding/input \
registers on TCP port 502, refreshed from iotbench-simd."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://iotbench-modbusd.c \
           file://iotbench-modbusd.service"

S = "${UNPACKDIR}"

DEPENDS += "libmodbus"

inherit systemd pkgconfig

SYSTEMD_SERVICE:${PN} = "iotbench-modbusd.service"
RDEPENDS:${PN} = "libmodbus"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-modbusd.c -o ${B}/iotbench-modbusd \
        `pkg-config --cflags --libs libmodbus`
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-modbusd ${D}${bindir}/iotbench-modbusd

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-modbusd.service ${D}${systemd_system_unitdir}/iotbench-modbusd.service
}

FILES:${PN} += "${systemd_system_unitdir}/iotbench-modbusd.service"
