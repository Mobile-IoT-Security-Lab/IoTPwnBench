SUMMARY = "IoTBench synthetic fixture - CWE-521 SSH empty-password policy"
DESCRIPTION = "Configuration-only research fixture. Installs no SSH server, accounts, credentials or startup hooks."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE file://sshd_config"
S = "${UNPACKDIR}"

# No dependency on openssh-sshd: this package contains data only.
do_install() {
    install -d ${D}${sysconfdir}/ssh
    install -m 0644 ${S}/sshd_config ${D}${sysconfdir}/ssh/sshd_config
}

FILES:${PN} = "${sysconfdir}/ssh/sshd_config"
CONFFILES:${PN} = "${sysconfdir}/ssh/sshd_config"
