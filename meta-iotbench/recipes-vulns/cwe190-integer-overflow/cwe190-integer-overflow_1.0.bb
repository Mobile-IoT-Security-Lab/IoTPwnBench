SUMMARY = "IoTBench fixture - CWE-190 native C integer overflow"
DESCRIPTION = "Intentionally unchecked uint32_t multiplication of a parsed synthetic record count. Local testing only; not for deployment."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://fixture-batch-size.c file://NOTICE file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "virtual/libc"
RDEPENDS:${PN} = "busybox util-linux-setpriv"

# Preserve the input parser, 32-bit multiplication, and consumer for analysis.
# Fortify requires optimization; only this buffer-free -O0 helper undefines it.
# Sanitizers belong to separate local diagnostic builds, never the image.
INHIBIT_PACKAGE_STRIP = "1"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -O0 -g -fno-inline -fno-lto -U_FORTIFY_SOURCE ${LDFLAGS} \
        -std=c99 -Wall -Wextra -Werror ${S}/fixture-batch-size.c \
        -o ${B}/fixture-batch-size
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/integer-overflow
    install -m 0755 ${B}/fixture-batch-size ${D}${bindir}/fixture-batch-size
    for fixture_file in LICENSE NOTICE fixture-batch-size.c; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/integer-overflow/$fixture_file
    done
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@DATADIR@|${datadir}|g' -e 's|@BINDIR@|${bindir}|g' \
            -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/$fixture_file \
            > ${D}${datadir}/iotbench/integer-overflow/$fixture_file
        chmod 0644 ${D}${datadir}/iotbench/integer-overflow/$fixture_file
    done
}

FILES:${PN} = "${bindir}/fixture-batch-size ${datadir}/iotbench/integer-overflow"
