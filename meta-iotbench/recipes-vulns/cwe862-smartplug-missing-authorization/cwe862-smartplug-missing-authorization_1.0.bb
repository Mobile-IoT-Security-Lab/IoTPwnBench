SUMMARY = "IoTBench smart plug missing authorization"
DESCRIPTION = "An MQTT relay controller validates the target and state but never verifies whether the requesting actor owns the plug. Inspired by CVE-2023-1750; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-smartplug-control \
           file://iotbench-smartplug-control.service \
           file://mosquitto-iotbench.conf \
           file://mosquitto-iotbench.service.conf"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-smartplug-control.service"
RDEPENDS:${PN} = "device-smartplug mosquitto mosquitto-clients"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/iotbench-smartplug-control ${D}${bindir}/iotbench-smartplug-control
    install -d ${D}${sysconfdir}/mosquitto
    install -m 0644 ${S}/mosquitto-iotbench.conf ${D}${sysconfdir}/mosquitto/iotbench.conf
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-smartplug-control.service ${D}${systemd_system_unitdir}/iotbench-smartplug-control.service
    install -d ${D}${systemd_system_unitdir}/mosquitto.service.d
    install -m 0644 ${S}/mosquitto-iotbench.service.conf ${D}${systemd_system_unitdir}/mosquitto.service.d/10-iotbench-listener.conf
}

FILES:${PN} = "${bindir}/iotbench-smartplug-control \
               ${sysconfdir}/mosquitto/iotbench.conf \
               ${systemd_system_unitdir}/iotbench-smartplug-control.service \
               ${systemd_system_unitdir}/mosquitto.service.d"
