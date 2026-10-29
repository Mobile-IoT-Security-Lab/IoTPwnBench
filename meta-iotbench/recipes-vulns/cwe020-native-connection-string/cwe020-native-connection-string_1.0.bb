SUMMARY = "IoTBench fixture - CWE-20 native SQLite connection string injection"
DESCRIPTION = "One intentionally missing cache-value validation; local synthetic research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://fixture-connection.c file://fixture-resource.h file://fixture-isolate.h file://Makefile file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "sqlite3"
RDEPENDS:${PN} = "busybox util-linux-setpriv"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_CONNECTION_FIXTURE ?= "0"
CFLAGS:append = " -fstack-protector-strong -fPIE"
LDFLAGS:append = " -pie -Wl,-z,relro,-z,now,-z,noexecstack"

python __anonymous() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_CONNECTION_FIXTURE') != '1'):
        raise bb.parse.SkipRecipe('Native connection fixture requires explicit opt-in and fixture mode')
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_CONNECTION_FIXTURE"
do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${LDFLAGS} -std=c99 -Wall -Wextra -Werror \
        -DIOTBENCH_CONNECTION_FIXTURE_ENABLED=1 ${S}/fixture-connection.c \
        -lsqlite3 -o ${B}/fixture-connection
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/native-connection-string
    install -m 0755 ${B}/fixture-connection ${D}${bindir}/fixture-connection
    for fixture_file in LICENSE NOTICE fixture-connection.c fixture-resource.h fixture-isolate.h Makefile ground-truth.json; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/native-connection-string/$fixture_file
    done
    sed -e 's|@BINDIR@|${bindir}|g' -e 's|@DATADIR@|${datadir}|g' \
        -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/test-guest.sh \
        > ${D}${datadir}/iotbench/native-connection-string/test-guest.sh
    chmod 0644 ${D}${datadir}/iotbench/native-connection-string/test-guest.sh
}

FILES:${PN} = "${bindir}/fixture-connection ${datadir}/iotbench/native-connection-string"
