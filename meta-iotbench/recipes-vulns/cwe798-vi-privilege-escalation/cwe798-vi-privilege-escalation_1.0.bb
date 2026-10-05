SUMMARY = "IoTBench vulnerability module - CWE-798 hardcoded maintenance credential"
DESCRIPTION = "A firmware-wide maintenance password grants the routerweb account SSH access and authorizes its privileged editor command. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-vi-sudoers"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard sudo busybox dropbear"

do_install() {
    install -d ${D}${sysconfdir}/sudoers.d
    install -m 0440 ${S}/iotbench-vi-sudoers ${D}${sysconfdir}/sudoers.d/iotbench-vi
}

FILES:${PN} = "${sysconfdir}/sudoers.d/iotbench-vi"
