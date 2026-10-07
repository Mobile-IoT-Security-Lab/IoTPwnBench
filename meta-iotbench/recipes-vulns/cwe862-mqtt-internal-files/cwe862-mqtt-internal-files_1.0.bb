SUMMARY = "IoTBench fixture - CWE-862 MQTT internal-file exposure"
DESCRIPTION = "A local Mosquitto broker grants anonymous read access to two topics backed by fixed synthetic internal files. Local security research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://iotbench-mqtt-internal-files.c file://iotbench-mqtt-internal-files.service file://mosquitto-iotbench.conf file://mosquitto-iotbench.service.conf file://iotbench-mqtt.service.conf file://iotbench-public.acl file://iotbench-publish.acl file://device.conf file://maintenance.dat file://NOTICE file://ground-truth.json"
S = "${UNPACKDIR}"
DEPENDS += "mosquitto"
RDEPENDS:${PN} = "mosquitto"

inherit systemd useradd

SYSTEMD_SERVICE:${PN} = "iotbench-mqtt-internal-files.service"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 991 mqttfixture"
USERADD_PARAM:${PN} = "--system --uid 991 --gid mqttfixture --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' mqttfixture"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -Wall -Wextra -Werror \
        -DFIXTURE_INTERNAL_DIR='"${datadir}/iotbench/mqtt-internal-files/internal"' \
        ${S}/iotbench-mqtt-internal-files.c -o ${B}/iotbench-mqtt-internal-files -lmosquitto
}

do_install() {
    install -d ${D}${bindir} ${D}${systemd_system_unitdir} ${D}${datadir}/iotbench/mqtt-internal-files
    install -m 0755 ${B}/iotbench-mqtt-internal-files ${D}${bindir}/iotbench-mqtt-internal-files
    sed -e 's|@BINDIR@|${bindir}|g' ${S}/iotbench-mqtt-internal-files.service > ${D}${systemd_system_unitdir}/iotbench-mqtt-internal-files.service
    chmod 0644 ${D}${systemd_system_unitdir}/iotbench-mqtt-internal-files.service
    install -d -m 0750 ${D}${datadir}/iotbench/mqtt-internal-files/internal
    install -m 0640 ${S}/device.conf ${D}${datadir}/iotbench/mqtt-internal-files/internal/device.conf
    install -m 0640 ${S}/maintenance.dat ${D}${datadir}/iotbench/mqtt-internal-files/internal/maintenance.dat
    chown -R 0:991 ${D}${datadir}/iotbench/mqtt-internal-files/internal
    install -m 0644 ${S}/NOTICE ${D}${datadir}/iotbench/mqtt-internal-files/NOTICE
    install -m 0644 ${S}/iotbench-mqtt-internal-files.c ${D}${datadir}/iotbench/mqtt-internal-files/publisher.c
    sed -e 's|@BINDIR@|${bindir}|g' -e 's|@DATADIR@|${datadir}|g' ${S}/ground-truth.json > ${D}${datadir}/iotbench/mqtt-internal-files/ground-truth.json
    chmod 0644 ${D}${datadir}/iotbench/mqtt-internal-files/ground-truth.json
    install -d ${D}${sysconfdir}/mosquitto ${D}${systemd_system_unitdir}/mosquitto.service.d
    install -m 0644 ${S}/mosquitto-iotbench.conf ${D}${sysconfdir}/mosquitto/iotbench.conf
    install -m 0644 ${S}/iotbench-public.acl ${S}/iotbench-publish.acl ${D}${sysconfdir}/mosquitto/
    install -m 0644 ${S}/mosquitto-iotbench.service.conf ${D}${systemd_system_unitdir}/mosquitto.service.d/10-iotbench-listener.conf
    # Existing telemetry publisher uses the write-only guest-loopback listener.
    install -d ${D}${systemd_system_unitdir}/iotbench-mqtt.service.d
    install -m 0644 ${S}/iotbench-mqtt.service.conf ${D}${systemd_system_unitdir}/iotbench-mqtt.service.d/10-fixture-publisher.conf
}

FILES:${PN} = "${bindir}/iotbench-mqtt-internal-files ${systemd_system_unitdir}/iotbench-mqtt-internal-files.service ${systemd_system_unitdir}/mosquitto.service.d ${systemd_system_unitdir}/iotbench-mqtt.service.d ${sysconfdir}/mosquitto/iotbench.conf ${sysconfdir}/mosquitto/iotbench-public.acl ${sysconfdir}/mosquitto/iotbench-publish.acl ${datadir}/iotbench/mqtt-internal-files"
