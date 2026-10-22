SUMMARY = "IoTBench fixture - CWE-120 native C buffer overflow via local service"
DESCRIPTION = "Intentionally insecure synthetic fixture for local security testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://ground-truth.json file://fixture-label-service.c file://iotbench-label.service file://test-service.py file://test-guest.sh"
S = "${UNPACKDIR}"
IOTBENCH_ENABLE_CWE120_FIXTURE ?= "0"
python __anonymous() {
    if d.getVar("IOTBENCH_ENABLE_CWE120_FIXTURE") != "1":
        raise bb.parse.SkipRecipe("CWE-120 requires IOTBENCH_ENABLE_CWE120_FIXTURE = 1 in isolated test configuration")
}
DEPENDS = "virtual/libc gcc-runtime gcc-sanitizers"
RDEPENDS:${PN} = "python3-core python3-resource python3-io util-linux-setpriv"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iotbench-label.service"
# The one-request service is explicitly started only during isolated tests.
SYSTEMD_AUTO_ENABLE:${PN} = "disable"
INHIBIT_PACKAGE_STRIP = "1"

do_compile() {
    # Relative input paths keep ASan metadata independent of the build directory.
    cd ${S}
    # Preserve inherited Fortify, stack protection, PIE and linker hardening.
    ${CC} ${CPPFLAGS} ${CFLAGS} -DIOTBENCH_CWE120_FIXTURE=1 -g -fno-inline \
        -std=c99 -Wall -Wextra -Werror fixture-label-service.c ${LDFLAGS} -o ${B}/fixture-label-service
    # Separate diagnostic executable, never used by the registered firmware service.
    ${CC} ${CPPFLAGS} ${CFLAGS} -DIOTBENCH_CWE120_FIXTURE=1 -g -fno-inline \
        -fsanitize=address -fno-omit-frame-pointer -std=c99 -Wall -Wextra -Werror \
        fixture-label-service.c ${LDFLAGS} -fsanitize=address -o ${B}/fixture-label-service-asan
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/service-buffer-overflow ${D}${systemd_system_unitdir} ${D}${sysconfdir}/iotbench
    echo 'Synthetic CWE-120 fixture explicitly enabled at build time' > ${D}${sysconfdir}/iotbench/cwe120-fixture-enabled
    chmod 0644 ${D}${sysconfdir}/iotbench/cwe120-fixture-enabled
    install -m 0755 ${B}/fixture-label-service ${D}${bindir}/fixture-label-service
    install -m 0755 ${B}/fixture-label-service-asan ${D}${datadir}/iotbench/service-buffer-overflow/fixture-label-service-asan
    for fixture_file in LICENSE NOTICE ground-truth.json fixture-label-service.c test-service.py test-guest.sh; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/service-buffer-overflow/$fixture_file
    done
    install -m 0644 ${S}/iotbench-label.service ${D}${systemd_system_unitdir}/iotbench-label.service
}

FILES:${PN} = "${bindir}/fixture-label-service ${datadir}/iotbench/service-buffer-overflow ${systemd_system_unitdir}/iotbench-label.service ${sysconfdir}/iotbench/cwe120-fixture-enabled"
