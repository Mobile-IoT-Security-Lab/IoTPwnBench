SUMMARY = "IoTBench smart speaker ID3 heap overflow"
DESCRIPTION = "A network media-indexing service copies an ID3 title into a smaller heap field. Inspired by CVE-2025-1049; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-id3d.c file://iotbench-id3d.service"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-id3d.service"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-id3d.c -o ${B}/iotbench-id3d
}

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${B}/iotbench-id3d ${D}${sbindir}/iotbench-id3d
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-id3d.service ${D}${systemd_system_unitdir}/iotbench-id3d.service
}

FILES:${PN} = "${sbindir}/iotbench-id3d ${systemd_system_unitdir}/iotbench-id3d.service"
