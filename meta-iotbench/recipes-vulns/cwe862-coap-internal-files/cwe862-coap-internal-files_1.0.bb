SUMMARY = "IoTBench fixture - CWE-862 CoAP internal-file exposure"
DESCRIPTION = "A read-only CoAP daemon exposes two predefined synthetic internal files without authorization. Local security research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://iotbench-coap-internal-files.c file://iotbench-coap-internal-files.service file://device.conf file://maintenance.dat file://NOTICE file://ground-truth.json"
S = "${UNPACKDIR}"
DEPENDS += "libcoap"
RDEPENDS:${PN} += "python3-core python3-modules"

inherit systemd useradd pkgconfig

SYSTEMD_SERVICE:${PN} = "iotbench-coap-internal-files.service"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 960 coapfixture"
USERADD_PARAM:${PN} = "--system --uid 960 --gid coapfixture --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' coapfixture"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -Wall -Wextra -Werror \
        -DFIXTURE_INTERNAL_DIR='"${datadir}/iotbench/coap-internal-files/internal"' \
        ${S}/iotbench-coap-internal-files.c -o ${B}/iotbench-coap-internal-files \
        $(pkg-config --cflags --libs libcoap-3-openssl)
}

do_install() {
    install -d ${D}${bindir} ${D}${systemd_system_unitdir} ${D}${datadir}/iotbench/coap-internal-files
    install -m 0755 ${B}/iotbench-coap-internal-files ${D}${bindir}/iotbench-coap-internal-files
    sed -e 's|@BINDIR@|${bindir}|g' ${S}/iotbench-coap-internal-files.service > ${D}${systemd_system_unitdir}/iotbench-coap-internal-files.service
    chmod 0644 ${D}${systemd_system_unitdir}/iotbench-coap-internal-files.service
    install -d -m 0750 ${D}${datadir}/iotbench/coap-internal-files/internal
    install -m 0640 ${S}/device.conf ${D}${datadir}/iotbench/coap-internal-files/internal/device.conf
    install -m 0640 ${S}/maintenance.dat ${D}${datadir}/iotbench/coap-internal-files/internal/maintenance.dat
    chown -R 0:960 ${D}${datadir}/iotbench/coap-internal-files/internal
    install -m 0644 ${S}/NOTICE ${D}${datadir}/iotbench/coap-internal-files/NOTICE
    # Install the short data-flow source alongside the ELF for static analysis.
    install -m 0644 ${S}/iotbench-coap-internal-files.c ${D}${datadir}/iotbench/coap-internal-files/handler.c
    sed -e 's|@BINDIR@|${bindir}|g' -e 's|@DATADIR@|${datadir}|g' ${S}/ground-truth.json > ${D}${datadir}/iotbench/coap-internal-files/ground-truth.json
    chmod 0644 ${D}${datadir}/iotbench/coap-internal-files/ground-truth.json
}

FILES:${PN} = "${bindir}/iotbench-coap-internal-files ${systemd_system_unitdir}/iotbench-coap-internal-files.service ${datadir}/iotbench/coap-internal-files"
