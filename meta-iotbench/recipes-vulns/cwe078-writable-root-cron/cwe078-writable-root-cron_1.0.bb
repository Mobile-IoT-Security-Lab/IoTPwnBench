SUMMARY = "IoTBench vulnerability module - CWE-78 root cron command injection"
DESCRIPTION = "A root-owned cron job interpolates a web-user-controlled maintenance target into a shell command. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-root-maintenance.cron file://cron-maintenance.sh file://maintenance-target"

S = "${UNPACKDIR}"

inherit useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --uid 995 --home-dir ${localstatedir}/lib/router-dashboard --no-create-home --shell /sbin/nologin --user-group routerweb"

RDEPENDS:${PN} = "router-dashboard cronie"

do_install() {
    install -d ${D}${sysconfdir}/cron.d
    install -m 0644 ${S}/iotbench-root-maintenance.cron ${D}${sysconfdir}/cron.d/iotbench-root-maintenance
    install -d -m 0750 ${D}${localstatedir}/lib/router-dashboard
    install -m 0755 ${S}/cron-maintenance.sh ${D}${localstatedir}/lib/router-dashboard/cron-maintenance.sh
    install -m 0664 ${S}/maintenance-target ${D}${localstatedir}/lib/router-dashboard/maintenance-target
    chown 995:995 ${D}${localstatedir}/lib/router-dashboard/maintenance-target
}

FILES:${PN} = "${sysconfdir}/cron.d/iotbench-root-maintenance \
               ${localstatedir}/lib/router-dashboard/cron-maintenance.sh \
               ${localstatedir}/lib/router-dashboard/maintenance-target"
