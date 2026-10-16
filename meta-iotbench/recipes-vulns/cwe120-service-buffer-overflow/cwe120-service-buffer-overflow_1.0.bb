SUMMARY = "IoTBench fixture - CWE-120 native C buffer overflow via local service"
DESCRIPTION = "Intentionally insecure synthetic fixture for local security testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json file://fixture-label-service.c file://iotbench-label.service file://test-service.py file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "virtual/libc gcc-runtime"
RDEPENDS:${PN} = "python3-core python3-resource python3-subprocess python3-tempfile python3-netclient python3-argparse util-linux-setpriv"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-label.service"
# The one-request service is explicitly started only during isolated tests.
SYSTEMD_AUTO_ENABLE:${PN} = "disable"
INHIBIT_PACKAGE_STRIP = "1"

do_compile() {
    # Keep the recognizable strcpy call and handler. Retain stack protection/NX.
    # Fortify requires optimization and would change the intentionally unsafe sink.
    ${CC} ${CPPFLAGS} ${CFLAGS} -O0 -g -fno-inline -fno-lto -fno-builtin-strcpy -U_FORTIFY_SOURCE \
        -std=c99 -Wall -Wextra -Werror ${S}/fixture-label-service.c ${LDFLAGS} -o ${B}/fixture-label-service
    # Separate diagnostic executable, never used by the registered firmware service.
    ${CC} ${CPPFLAGS} ${CFLAGS} -O0 -g -fno-inline -fno-lto -fno-builtin-strcpy -U_FORTIFY_SOURCE \
        -fsanitize=address -fno-omit-frame-pointer -std=c99 -Wall -Wextra -Werror \
        ${S}/fixture-label-service.c ${LDFLAGS} -fsanitize=address -o ${B}/fixture-label-service-asan
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/service-buffer-overflow ${D}${systemd_system_unitdir}
    install -m 0755 ${B}/fixture-label-service ${D}${bindir}/fixture-label-service
    install -m 0755 ${B}/fixture-label-service-asan ${D}${datadir}/iotbench/service-buffer-overflow/fixture-label-service-asan
    for fixture_file in LICENSE NOTICE ground-truth.json fixture-label-service.c test-service.py test-guest.sh; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/service-buffer-overflow/$fixture_file
    done
    install -m 0644 ${S}/iotbench-label.service ${D}${systemd_system_unitdir}/iotbench-label.service
}

FILES:${PN} = "${bindir}/fixture-label-service ${datadir}/iotbench/service-buffer-overflow ${systemd_system_unitdir}/iotbench-label.service"
