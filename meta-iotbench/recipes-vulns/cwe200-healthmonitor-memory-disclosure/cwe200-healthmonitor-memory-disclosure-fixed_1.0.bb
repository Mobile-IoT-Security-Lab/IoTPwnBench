require recipes-vulns/cwe200-healthmonitor-memory-disclosure/cwe200-healthmonitor-memory-disclosure_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-200 health monitor memory disclosure"
DESCRIPTION = "Corrected twin of cwe200-healthmonitor-memory-disclosure. Memory is returned only to a peer that presents the operator key. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
SRC_URI += "file://iotbench-healthd.key"

do_install:append() {
    install -d -m 0755 ${D}${sysconfdir}/iotbench
    install -m 0600 ${S}/iotbench-healthd.key ${D}${sysconfdir}/iotbench/healthd.key
}

FILES:${PN} += "${sysconfdir}/iotbench/healthd.key"
