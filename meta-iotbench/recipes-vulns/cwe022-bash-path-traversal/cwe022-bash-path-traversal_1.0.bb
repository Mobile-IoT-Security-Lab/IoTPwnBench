SUMMARY = "IoTBench fixture - CWE-22 vulnerable Bash file path traversal"
DESCRIPTION = "Intentionally unvalidated Bash path concatenation reads synthetic internal data outside the intended data directory. A fixed process jail contains all reads. Local testing only."
LICENSE = "MIT & GPL-3.0-or-later"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7 \
                    file://${COMMON_LICENSE_DIR}/GPL-3.0-or-later;md5=1c76c4cc354acaac30ed4d5eefea7245"
SRC_URI = "file://LICENSE file://iotbench-bash-read file://fixture-confine.c \
           file://public.txt file://private-fixture.txt file://NOTICE \
           file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS = "bash"
RDEPENDS:${PN} = "bash busybox"

do_compile() {
    # Safe Bash loadable builtin, not a standalone executable or vulnerable sink.
    ${CC} ${CPPFLAGS} ${CFLAGS} -Wall -Wextra -Werror -fPIC -shared \
        -I${STAGING_INCDIR}/bash -I${STAGING_INCDIR}/bash/include \
        -DFIXTURE_JAIL='"${datadir}/iotbench/bash-path-traversal/rootfs"' \
        ${S}/fixture-confine.c ${LDFLAGS} -o ${B}/fixture-confine.so
}

do_install() {
    fixture_dir=${datadir}/iotbench/bash-path-traversal
    install -d ${D}${bindir} ${D}${libdir}/iotbench/bash-path-traversal \
        ${D}$fixture_dir/rootfs$fixture_dir/data ${D}$fixture_dir/rootfs$fixture_dir/internal
    install -m 0755 ${B}/fixture-confine.so ${D}${libdir}/iotbench/bash-path-traversal/fixture-confine.so
    sed -e 's|@DATADIR@|${datadir}|g' -e 's|@LIBDIR@|${libdir}|g' \
        ${S}/iotbench-bash-read > ${D}${bindir}/iotbench-bash-read
    chmod 0755 ${D}${bindir}/iotbench-bash-read
    install -m 0644 ${S}/public.txt ${D}$fixture_dir/rootfs$fixture_dir/data/public.txt
    install -m 0644 ${S}/private-fixture.txt ${D}$fixture_dir/rootfs$fixture_dir/internal/private-fixture.txt
    install -m 0644 ${S}/NOTICE ${D}$fixture_dir/NOTICE
    install -m 0644 ${S}/fixture-confine.c ${D}$fixture_dir/fixture-confine.c
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@DATADIR@|${datadir}|g' -e 's|@LIBDIR@|${libdir}|g' \
            -e 's|@BINDIR@|${bindir}|g' ${S}/$fixture_file > ${D}$fixture_dir/$fixture_file
        chmod 0644 ${D}$fixture_dir/$fixture_file
    done
}

FILES:${PN} = "${bindir}/iotbench-bash-read ${libdir}/iotbench/bash-path-traversal ${datadir}/iotbench/bash-path-traversal"
