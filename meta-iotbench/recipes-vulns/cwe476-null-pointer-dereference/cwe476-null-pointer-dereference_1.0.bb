SUMMARY = "IoTBench fixture - CWE-476 native C null pointer dereference"
DESCRIPTION = "Intentionally insecure input-dependent synthetic record lookup in a native C binary. Local testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://fixture-device-info.c file://test-null-dereference.c file://NOTICE file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "virtual/libc"
RDEPENDS:${PN} = "busybox util-linux-setpriv"

# Preserve the small lookup, its nullable return, member load and symbol names
# for firmware analysis. Sanitizers are only used in separate local test builds.
# glibc's fortify wrappers require optimization; undefine that macro only for
# this buffer-free -O0 fixture, retaining the other Yocto hardening flags.
INHIBIT_PACKAGE_STRIP = "1"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -O0 -g -fno-inline -fno-lto -U_FORTIFY_SOURCE ${LDFLAGS} \
        -std=c99 -Wall -Wextra -Werror ${S}/fixture-device-info.c \
        -o ${B}/fixture-device-info
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c99 -Wall -Wextra -Werror \
        -DFIXTURE_HELPER='"${bindir}/fixture-device-info"' \
        ${S}/test-null-dereference.c -o ${B}/test-null-dereference
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/null-pointer-dereference
    install -m 0755 ${B}/fixture-device-info ${D}${bindir}/fixture-device-info
    install -m 0755 ${B}/test-null-dereference ${D}${datadir}/iotbench/null-pointer-dereference/test-null-dereference
    for fixture_file in LICENSE NOTICE fixture-device-info.c test-null-dereference.c; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/null-pointer-dereference/$fixture_file
    done
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@DATADIR@|${datadir}|g' -e 's|@BINDIR@|${bindir}|g' \
            -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/$fixture_file \
            > ${D}${datadir}/iotbench/null-pointer-dereference/$fixture_file
        chmod 0644 ${D}${datadir}/iotbench/null-pointer-dereference/$fixture_file
    done
}

FILES:${PN} = "${bindir}/fixture-device-info ${datadir}/iotbench/null-pointer-dereference"
