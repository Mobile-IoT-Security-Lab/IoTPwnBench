SUMMARY = "IoTBench vulnerability module - CWE-276 anonymous FTP login"
DESCRIPTION = "Permissive default FTP access exposes a device maintenance backup to anonymous users. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://vsftpd-anonymous.conf \
           file://20-iotbench-anonymous.conf \
           file://iotbench-anonymous-backup \
           file://README.txt"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "vsftpd router-dashboard"

do_install() {
    install -d ${D}${sysconfdir}/iotbench
    install -m 0644 ${S}/vsftpd-anonymous.conf ${D}${sysconfdir}/iotbench/vsftpd-anonymous.conf
    install -d ${D}${libexecdir}
    install -m 0755 ${S}/iotbench-anonymous-backup ${D}${libexecdir}/iotbench-anonymous-backup
    install -d ${D}${systemd_system_unitdir}/vsftpd.service.d
    sed -e 's|@SBINDIR@|${sbindir}|g' \
        -e 's|@LIBEXECDIR@|${libexecdir}|g' \
        -e 's|@SYSCONFDIR@|${sysconfdir}|g' \
        ${S}/20-iotbench-anonymous.conf > ${D}${systemd_system_unitdir}/vsftpd.service.d/20-iotbench-anonymous.conf
    install -d -m 0755 ${D}${localstatedir}/lib/ftp
    install -m 0644 ${S}/README.txt ${D}${localstatedir}/lib/ftp/README.txt
}

FILES:${PN} = "${sysconfdir}/iotbench/vsftpd-anonymous.conf \
               ${libexecdir}/iotbench-anonymous-backup \
               ${systemd_system_unitdir}/vsftpd.service.d/20-iotbench-anonymous.conf \
               ${localstatedir}/lib/ftp"
CONFFILES:${PN} = "${sysconfdir}/iotbench/vsftpd-anonymous.conf"
