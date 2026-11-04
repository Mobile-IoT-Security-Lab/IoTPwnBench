require recipes-vulns/cwe306-envsensor-unauth-calibration/cwe306-envsensor-unauth-calibration_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-306 environmental sensor unauthenticated calibration"
DESCRIPTION = "Corrected twin of cwe306-envsensor-unauth-calibration. Calibration needs the device token. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
SRC_URI += "file://calibration.token"

do_install:append() {
    install -d -m 0755 ${D}${sysconfdir}/iotbench
    install -m 0600 ${S}/calibration.token ${D}${sysconfdir}/iotbench/calibration.token
}

FILES:${PN} += "${sysconfdir}/iotbench/calibration.token"
