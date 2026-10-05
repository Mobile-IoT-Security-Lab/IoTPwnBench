SUMMARY = "IoTBench MQTT authentication replay"
DESCRIPTION = "A device accepts a previously authenticated control frame repeatedly because it does not enforce sequence freshness. Models RF/BLE-to-gateway replay such as CVE-2023-46892 and CVE-2018-16242; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-mqtt-replay \
           file://iotbench-mqtt-replay.service \
           file://mosquitto-iotbench.conf \
           file://mosquitto-iotbench.service.conf"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-mqtt-replay.service"
RDEPENDS:${PN} = "mosquitto mosquitto-clients"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/iotbench-mqtt-replay ${D}${bindir}/iotbench-mqtt-replay
    install -d ${D}${sysconfdir}/mosquitto
    install -m 0644 ${S}/mosquitto-iotbench.conf ${D}${sysconfdir}/mosquitto/iotbench.conf
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-mqtt-replay.service ${D}${systemd_system_unitdir}/iotbench-mqtt-replay.service
    install -d ${D}${systemd_system_unitdir}/mosquitto.service.d
    install -m 0644 ${S}/mosquitto-iotbench.service.conf ${D}${systemd_system_unitdir}/mosquitto.service.d/10-iotbench-listener.conf
}

FILES:${PN} = "${bindir}/iotbench-mqtt-replay \
               ${sysconfdir}/mosquitto/iotbench.conf \
               ${systemd_system_unitdir}/iotbench-mqtt-replay.service \
               ${systemd_system_unitdir}/mosquitto.service.d"
