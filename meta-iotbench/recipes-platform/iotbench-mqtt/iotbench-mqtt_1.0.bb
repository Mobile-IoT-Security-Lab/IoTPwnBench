SUMMARY = "IoTBench MQTT telemetry publisher"
DESCRIPTION = "Publishes simulated peripheral values from iotbench-simd to the \
local MQTT broker, under iotbench/<device-class>/<peripheral> topics."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://iotbench-mqtt-publish.sh \
           file://iotbench-mqtt.service"

S = "${UNPACKDIR}"

inherit systemd

SYSTEMD_SERVICE:${PN} = "iotbench-mqtt.service"

# Local broker + command-line publisher.
RDEPENDS:${PN} = "mosquitto mosquitto-clients"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/iotbench-mqtt-publish.sh ${D}${bindir}/iotbench-mqtt-publish

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-mqtt.service ${D}${systemd_system_unitdir}/iotbench-mqtt.service
}

FILES:${PN} += "${systemd_system_unitdir}/iotbench-mqtt.service"
