SUMMARY = "IoTBench vulnerability module - CWE-276 SSH root login permitted"
DESCRIPTION = "Enables direct root password login through OpenSSH using the existing firmware lab credential. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE file://00-iotbench-permit-root-login.conf"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "openssh-sshd"

do_install() {
    install -d ${D}${sysconfdir}/ssh/sshd_config.d
    install -m 0644 ${S}/00-iotbench-permit-root-login.conf ${D}${sysconfdir}/ssh/sshd_config.d/00-iotbench-permit-root-login.conf
}

FILES:${PN} = "${sysconfdir}/ssh/sshd_config.d/00-iotbench-permit-root-login.conf"
CONFFILES:${PN} = "${sysconfdir}/ssh/sshd_config.d/00-iotbench-permit-root-login.conf"
