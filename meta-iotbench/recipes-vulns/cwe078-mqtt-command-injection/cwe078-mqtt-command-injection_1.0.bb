SUMMARY = "IoTBench MQTT maintenance command injection"
DESCRIPTION = "A privileged device maintenance agent consumes an unauthenticated MQTT message and interpolates its payload into a shell command. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=f5b1129dfbfc8afc083db247ff942d07"

SRC_URI = "file://LICENSE \
           file://iotbench-mqtt-maintenance \
           file://iotbench-mqtt-maintenance.service \
           file://mosquitto-iotbench.conf \
           file://mosquitto-iotbench.service.conf"

S = "${UNPACKDIR}"

inherit systemd

SYSTEMD_SERVICE:${PN} = "iotbench-mqtt-maintenance.service"
RDEPENDS:${PN} = "mosquitto mosquitto-clients"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/iotbench-mqtt-maintenance ${D}${bindir}/iotbench-mqtt-maintenance

    install -d ${D}${sysconfdir}/mosquitto
    install -m 0644 ${S}/mosquitto-iotbench.conf ${D}${sysconfdir}/mosquitto/iotbench.conf

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-mqtt-maintenance.service \
        ${D}${systemd_system_unitdir}/iotbench-mqtt-maintenance.service
    install -d ${D}${systemd_system_unitdir}/mosquitto.service.d
    install -m 0644 ${S}/mosquitto-iotbench.service.conf \
        ${D}${systemd_system_unitdir}/mosquitto.service.d/10-iotbench-listener.conf
}

FILES:${PN} = "${bindir}/iotbench-mqtt-maintenance \
               ${sysconfdir}/mosquitto/iotbench.conf \
               ${systemd_system_unitdir}/iotbench-mqtt-maintenance.service \
               ${systemd_system_unitdir}/mosquitto.service.d"
