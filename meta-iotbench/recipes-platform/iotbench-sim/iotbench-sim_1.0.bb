SUMMARY = "IoTBench shared peripheral simulator daemon"
DESCRIPTION = "Reads a per-device peripheral spec and writes a JSON snapshot of \
live, realistically varying values that device skeletons expose over their \
native protocol. The peripheral spec is provided by each device package."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://iotbench-simd.c \
           file://iotbench-sim.service"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"

inherit systemd

SYSTEMD_SERVICE:${PN} = "iotbench-sim.service"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-simd.c -o ${B}/iotbench-simd -lm
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/iotbench-simd ${D}${bindir}/iotbench-simd

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-sim.service ${D}${systemd_system_unitdir}/iotbench-sim.service
}

FILES:${PN} += "${systemd_system_unitdir}/iotbench-sim.service"
