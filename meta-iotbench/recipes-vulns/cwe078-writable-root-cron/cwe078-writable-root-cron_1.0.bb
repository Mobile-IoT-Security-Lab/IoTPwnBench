SUMMARY = "IoTBench vulnerability module - CWE-78 writable root cron script"
DESCRIPTION = "Installs a root cron entry that calls a web-user-writable script. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://module.php file://iotbench-root-maintenance.cron file://cron-maintenance.sh"

S = "${UNPACKDIR}"

inherit useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --uid 995 --home-dir ${localstatedir}/lib/router-dashboard --no-create-home --shell /sbin/nologin --user-group routerweb"

RDEPENDS:${PN} = "router-dashboard cronie"

do_install() {
    install -d ${D}${sysconfdir}/cron.d
    install -m 0644 ${S}/iotbench-root-maintenance.cron ${D}${sysconfdir}/cron.d/iotbench-root-maintenance
    install -d -m 0750 ${D}${localstatedir}/lib/router-dashboard
    install -m 0775 ${S}/cron-maintenance.sh ${D}${localstatedir}/lib/router-dashboard/cron-maintenance.sh
    chown 995:995 ${D}${localstatedir}/lib/router-dashboard/cron-maintenance.sh
    install -d ${D}${datadir}/router-dashboard/modules/writable-cron
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/writable-cron/module.php
}

FILES:${PN} = "${sysconfdir}/cron.d/iotbench-root-maintenance ${localstatedir}/lib/router-dashboard/cron-maintenance.sh ${datadir}/router-dashboard/modules/writable-cron"
