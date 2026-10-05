SUMMARY = "IoTBench vulnerability module - CWE-798 hardcoded support credential"
DESCRIPTION = "A firmware-wide support password grants the routerweb account SSH access and authorizes its restricted LD_PRELOAD-capable sudo command. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ldpreload-target.c file://preload-marker.c file://iotbench-ldpreload-sudoers"

S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard sudo dropbear"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/ldpreload-target.c -o ${B}/ldpreload-target
    ${CC} ${CFLAGS} ${LDFLAGS} -fPIC -shared ${S}/preload-marker.c -o ${B}/preload-marker.so
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/ldpreload-target ${D}${bindir}/ldpreload-target
    install -d ${D}${libdir}/iotbench
    install -m 0755 ${B}/preload-marker.so ${D}${libdir}/iotbench/preload-marker.so
    install -d ${D}${sysconfdir}/sudoers.d
    install -m 0440 ${S}/iotbench-ldpreload-sudoers ${D}${sysconfdir}/sudoers.d/iotbench-ldpreload
}

FILES:${PN} = "${bindir}/ldpreload-target ${libdir}/iotbench/preload-marker.so ${sysconfdir}/sudoers.d/iotbench-ldpreload"
