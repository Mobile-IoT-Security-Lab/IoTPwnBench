SUMMARY = "IoTBench environmental sensor missing authentication"
DESCRIPTION = "A network data logger exposes calibration changes without authenticating the caller. Inspired by CVE-2023-23545; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iotbench-envsensor-calibration \
           file://iotbench-envsensor-calibration.service \
           file://mosquitto-iotbench.conf \
           file://mosquitto-iotbench.service.conf"
S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-envsensor-calibration.service"
RDEPENDS:${PN} = "device-envsensor mosquitto mosquitto-clients"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/iotbench-envsensor-calibration ${D}${bindir}/iotbench-envsensor-calibration
    install -d ${D}${sysconfdir}/mosquitto
    install -m 0644 ${S}/mosquitto-iotbench.conf ${D}${sysconfdir}/mosquitto/iotbench.conf
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/iotbench-envsensor-calibration.service ${D}${systemd_system_unitdir}/iotbench-envsensor-calibration.service
    install -d ${D}${systemd_system_unitdir}/mosquitto.service.d
    install -m 0644 ${S}/mosquitto-iotbench.service.conf ${D}${systemd_system_unitdir}/mosquitto.service.d/10-iotbench-listener.conf
}

FILES:${PN} = "${bindir}/iotbench-envsensor-calibration \
               ${sysconfdir}/mosquitto/iotbench.conf \
               ${systemd_system_unitdir}/iotbench-envsensor-calibration.service \
               ${systemd_system_unitdir}/mosquitto.service.d"
