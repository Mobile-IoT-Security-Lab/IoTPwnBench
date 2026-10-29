SUMMARY = "IoTBench synthetic vsftpd bad write rights (CWE-276)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://vsftpd.conf file://pam file://ftp-users file://readme.txt file://iotbench-ftp-write.service file://test-guest.py file://policy.json"
S = "${UNPACKDIR}"
REQUIRED_DISTRO_FEATURES = "pam systemd"
inherit useradd features_check
RDEPENDS:${PN} = "vsftpd libpam pam-plugin-unix python3-modules util-linux-nsenter"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system ftpfixture"
USERADD_PARAM:${PN} = "--system --gid ftpfixture --home-dir /srv/iotbench-ftp --no-create-home --shell /bin/false --password '\$6\$iotftpfixture\$ZtLuP9ED4aZz4B.j/q4xgCtTM83BE5ZWM0raCgY2oRr0D8p3XsmhMsNDklE9BQj8UYy4d7JCw6T9e1776NEAn0' ftpfixture"

do_install() {
    install -d -m 0555 ${D}/var/empty/vsftpd
    install -d ${D}${sysconfdir}/iotbench ${D}${sysconfdir}/pam.d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/vsftpd.conf ${D}${sysconfdir}/iotbench/vsftpd-write-rights.conf
    install -m 0644 ${S}/ftp-users ${D}${sysconfdir}/iotbench/ftp-users
    install -m 0644 ${S}/pam ${D}${sysconfdir}/pam.d/iotbench-ftp
    sed 's|@SBINDIR@|${sbindir}|g' ${S}/iotbench-ftp-write.service > ${D}${systemd_system_unitdir}/iotbench-ftp-write.service
    install -d -m 0755 ${D}/srv/iotbench-ftp ${D}/srv/iotbench-ftp/control
    install -d -m 0775 ${D}/srv/iotbench-ftp/bad
    chown root:ftpfixture ${D}/srv/iotbench-ftp/bad ${D}/srv/iotbench-ftp/control
    for directory in bad control; do
        install -m 0644 ${S}/readme.txt ${D}/srv/iotbench-ftp/$directory/readme.txt
    done
    install -d ${D}${datadir}/iotbench/bad-write-rights
    install -m 0644 ${S}/policy.json ${D}${datadir}/iotbench/bad-write-rights/policy.json
    install -m 0644 ${S}/test-guest.py ${D}${datadir}/iotbench/bad-write-rights/test-guest.py
}
FILES:${PN} += "/var/empty/vsftpd /srv/iotbench-ftp ${systemd_system_unitdir}/iotbench-ftp-write.service ${datadir}/iotbench/bad-write-rights"
