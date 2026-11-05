SUMMARY = "IoTBench fixture - CWE-787 native C configuration buffer overflow"
DESCRIPTION = "Synthetic indexed out-of-bounds write; CWE-20 contributes and CWE-119 is the broader category. Local research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://NOTICE file://fixture-buffer-write.c file://ground-truth.json file://test-guest.sh file://Makefile"
S = "${UNPACKDIR}"
DEPENDS = "virtual/libc"
RDEPENDS:${PN} = "busybox util-linux-setpriv"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE ?= "0"
PACKAGECONFIG ??= ""
PACKAGECONFIG[asan] = ",,gcc-sanitizers,libasan"
# The fixture compiles directly in do_compile; its shipped Makefile is an
# offline reference and deliberately has no clean target for do_configure.
do_configure[noexec] = "1"
CFLAGS:append = " -fstack-protector-strong -fPIE"
LDFLAGS:append = " -pie -Wl,-z,relro,-z,now,-z,noexecstack"

python __anonymous() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE') != '1'):
        raise bb.parse.SkipRecipe('Native buffer fixture requires explicit opt-in and fixture mode')
}

# Keep the input parser, indexed store and symbols recognizable. Retain Yocto's
# hardening flags, including fortify. ASan is an explicit test-build option.
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE PACKAGECONFIG"
do_compile() {
    # ASan records the source argument in its global-overflow diagnostic.
    # Compile from S so that the installed diagnostic ELF has no TMPDIR path.
    cd ${S}
    ${CC} ${CPPFLAGS} ${CFLAGS} -O1 -g -fno-inline -fno-lto ${LDFLAGS} \
        -DIOTBENCH_BUFFER_FIXTURE_ENABLED=1 -std=c99 -Wall -Wextra -Werror fixture-buffer-write.c \
        -o ${B}/fixture-buffer-write
    if ${@bb.utils.contains('PACKAGECONFIG', 'asan', 'true', 'false', d)}; then
        ${CC} ${CPPFLAGS} ${CFLAGS} -O1 -g -fno-inline -fno-lto ${LDFLAGS} \
            -DIOTBENCH_BUFFER_FIXTURE_ENABLED=1 -std=c99 -Wall -Wextra -Werror \
            -fsanitize=address -fno-sanitize-recover=all -fno-omit-frame-pointer \
            fixture-buffer-write.c -o ${B}/fixture-buffer-write-asan
    fi
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/native-buffer-overflow
    install -m 0755 ${B}/fixture-buffer-write ${D}${bindir}/fixture-buffer-write
    if ${@bb.utils.contains('PACKAGECONFIG', 'asan', 'true', 'false', d)}; then
        install -m 0755 ${B}/fixture-buffer-write-asan ${D}${bindir}/fixture-buffer-write-asan
    fi
    for fixture_file in LICENSE NOTICE fixture-buffer-write.c ground-truth.json Makefile; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/native-buffer-overflow/$fixture_file
    done
    sed -e 's|@BINDIR@|${bindir}|g' -e 's|@DATADIR@|${datadir}|g' \
        -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/test-guest.sh \
        > ${D}${datadir}/iotbench/native-buffer-overflow/test-guest.sh
    chmod 0644 ${D}${datadir}/iotbench/native-buffer-overflow/test-guest.sh
}

FILES:${PN} = "${bindir}/fixture-buffer-write ${bindir}/fixture-buffer-write-asan ${datadir}/iotbench/native-buffer-overflow"
