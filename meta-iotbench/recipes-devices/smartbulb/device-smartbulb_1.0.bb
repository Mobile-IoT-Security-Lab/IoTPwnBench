SUMMARY = "IoTBench smartbulb device profile"
DESCRIPTION = "Installs the smartbulb peripheral spec and identity, the shared web admin, and an MQTT publisher over a local broker."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE            file://peripherals.conf            file://device.conf"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = "router-dashboard mosquitto mosquitto-clients iotbench-mqtt"

do_install() {
    install -d ${D}${sysconfdir}/iotbench
    install -m 0644 ${S}/peripherals.conf ${D}${sysconfdir}/iotbench/peripherals.conf
    install -m 0644 ${S}/device.conf ${D}${sysconfdir}/iotbench/device.conf
}

FILES:${PN} = "${sysconfdir}/iotbench"
CONFFILES:${PN} = "${sysconfdir}/iotbench/peripherals.conf ${sysconfdir}/iotbench/device.conf"
