SUMMARY = "IoTBench vulnerability module - CWE-798 hardcoded credentials"
DESCRIPTION = "Vendor support backup access with a username and password embedded in the firmware and shared by every device. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE file://module.php file://support-backup.json"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${datadir}/router-dashboard/modules/hardcoded-credentials
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/hardcoded-credentials/module.php
    install -d ${D}${datadir}/iotbench/hardcoded-credentials
    install -m 0644 ${S}/support-backup.json ${D}${datadir}/iotbench/hardcoded-credentials/support-backup.json
}

FILES:${PN} = "${datadir}/router-dashboard/modules/hardcoded-credentials ${datadir}/iotbench/hardcoded-credentials"
