SUMMARY = "IoTBench synthetic fixture - CWE-521 SSH empty-password policy"
DESCRIPTION = "SSH policy fixture with a read-only dashboard diagnostic and corrected control. Installs no SSH server, accounts, credentials or startup hooks."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE file://sshd_config file://module.php"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard"

# No SSH daemon is needed for the read-only synthetic policy diagnostic.
do_install() {
    install -d ${D}${sysconfdir}/ssh
    install -m 0644 ${S}/sshd_config ${D}${sysconfdir}/ssh/sshd_config
    install -d ${D}${datadir}/router-dashboard/modules/ssh-empty-password-policy
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/ssh-empty-password-policy/module.php
}

FILES:${PN} = "${sysconfdir}/ssh/sshd_config ${datadir}/router-dashboard/modules/ssh-empty-password-policy"
CONFFILES:${PN} = "${sysconfdir}/ssh/sshd_config"
