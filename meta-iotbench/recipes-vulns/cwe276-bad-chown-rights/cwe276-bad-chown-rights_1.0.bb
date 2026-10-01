SUMMARY = "IoTBench vulnerability module - CWE-276 bad chown rights"
DESCRIPTION = "Installs a privileged configuration file owned by the web user. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://wan-policy.conf"

S = "${UNPACKDIR}"

inherit useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --uid 995 --home-dir ${localstatedir}/lib/router-dashboard --no-create-home --shell /sbin/nologin --user-group routerweb"

RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${datadir}/router-dashboard/modules/bad-chown
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/bad-chown/module.php

    install -d ${D}${sysconfdir}/iotbench
    install -m 0664 ${S}/wan-policy.conf ${D}${sysconfdir}/iotbench/wan-policy.conf
    chown 995:995 ${D}${sysconfdir}/iotbench/wan-policy.conf
}

FILES:${PN} = "${datadir}/router-dashboard/modules/bad-chown ${sysconfdir}/iotbench/wan-policy.conf"
CONFFILES:${PN} = "${sysconfdir}/iotbench/wan-policy.conf"
