SUMMARY = "IoTBench fixture - CWE-250 dangerous SUID rights"
DESCRIPTION = "A harmless synthetic identity reporter is unnecessarily installed root-owned with mode 4755, reachable by an unprivileged fixture user. Local research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://iotbench-suid-fixture.c file://NOTICE file://ground-truth.json"
S = "${UNPACKDIR}"
DEPENDS += "virtual/libc"
# Ordinary non-SUID verification tool for the guest root console. The synthetic
# executable below is the only SUID target introduced by this package.
RDEPENDS:${PN} = "util-linux-setpriv"

inherit useradd

USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 993 suidfixture"
USERADD_PARAM:${PN} = "--system --uid 993 --gid suidfixture --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' suidfixture"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -Wall -Wextra ${S}/iotbench-suid-fixture.c -o ${B}/iotbench-suid-fixture
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/iotbench/dangerous-suid-rights
    install -m 0755 ${B}/iotbench-suid-fixture ${D}${bindir}/iotbench-suid-fixture
    # Apply SUID last: changing ownership can clear the bit. Yocto's fakeroot
    # records root ownership and permissions for packaging and the ext4 image.
    chown 0:0 ${D}${bindir}/iotbench-suid-fixture
    chmod 4755 ${D}${bindir}/iotbench-suid-fixture
    install -m 0644 ${S}/NOTICE ${D}${datadir}/iotbench/dangerous-suid-rights/NOTICE
    sed -e 's|@BINDIR@|${bindir}|g' ${S}/ground-truth.json > ${D}${datadir}/iotbench/dangerous-suid-rights/ground-truth.json
    chmod 0644 ${D}${datadir}/iotbench/dangerous-suid-rights/ground-truth.json
}

FILES:${PN} = "${bindir}/iotbench-suid-fixture ${datadir}/iotbench/dangerous-suid-rights"
