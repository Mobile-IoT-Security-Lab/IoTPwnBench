SUMMARY = "IoTBench router device profile"
DESCRIPTION = "Installs the router peripheral spec (consumed by iotbench-simd) and device identity, and pulls in the shared web admin skeleton."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE            file://peripherals.conf            file://device.conf"

S = "${UNPACKDIR}"

# The shared device web admin (pulls in lighttpd + php).
RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}${sysconfdir}/iotbench
    install -m 0644 ${S}/peripherals.conf ${D}${sysconfdir}/iotbench/peripherals.conf
    install -m 0644 ${S}/device.conf ${D}${sysconfdir}/iotbench/device.conf
}

FILES:${PN} = "${sysconfdir}/iotbench"
CONFFILES:${PN} = "${sysconfdir}/iotbench/peripherals.conf ${sysconfdir}/iotbench/device.conf"
