SUMMARY = "IoTBench vulnerability module - CWE-798 privileged vi sudo rule"
DESCRIPTION = "Allows the web user to run BusyBox vi through sudo without a password. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://iotbench-vi-sudoers"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard sudo busybox"

do_install() {
    install -d ${D}${sysconfdir}/sudoers.d
    install -m 0440 ${S}/iotbench-vi-sudoers ${D}${sysconfdir}/sudoers.d/iotbench-vi
    install -d ${D}${datadir}/router-dashboard/modules/vi-privesc
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/vi-privesc/module.php
}

FILES:${PN} = "${sysconfdir}/sudoers.d/iotbench-vi ${datadir}/router-dashboard/modules/vi-privesc"
