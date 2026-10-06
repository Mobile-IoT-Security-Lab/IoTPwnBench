SUMMARY = "IoTBench vulnerability module - CWE-22 bad sudo rights path traversal"
DESCRIPTION = "Synthetic local-only sudo path traversal: a locked fixture user can read fake root-only data through a wildcard sudo rule and a privileged reader."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://maintenance-read.c file://iotbench-maintenance-sudoers \
           file://status.conf file://sudo-maintenance-secret.conf file://NOTICE \
           file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "sudo"

inherit useradd

USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 994 fixturetest"
USERADD_PARAM:${PN} = "--system --uid 994 --gid fixturetest --home-dir /nonexistent --no-create-home --shell /bin/false --password '!' fixturetest"

FIXTURE_ROOT = "${datadir}/iotbench/bad-sudo-rights"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} -Wall -Wextra \
        -DFIXTURE_ROOT='"${FIXTURE_ROOT}"' \
        ${S}/maintenance-read.c -o ${B}/iotbench-maintenance-read
}

do_install() {
    install -d ${D}${bindir} ${D}${sysconfdir}/sudoers.d
    install -m 0755 ${B}/iotbench-maintenance-read ${D}${bindir}/iotbench-maintenance-read
    sed -e 's|@BINDIR@|${bindir}|g' -e 's|@FIXTURE_ROOT@|${FIXTURE_ROOT}|g' ${S}/iotbench-maintenance-sudoers > ${D}${sysconfdir}/sudoers.d/iotbench-maintenance
    chmod 0440 ${D}${sysconfdir}/sudoers.d/iotbench-maintenance
    install -d -m 0755 ${D}${FIXTURE_ROOT} ${D}${FIXTURE_ROOT}/data
    install -d -m 0700 ${D}${FIXTURE_ROOT}/private
    install -m 0644 ${S}/status.conf ${D}${FIXTURE_ROOT}/data/status.conf
    install -m 0600 ${S}/sudo-maintenance-secret.conf ${D}${FIXTURE_ROOT}/private/root-only.conf
    install -m 0644 ${S}/NOTICE ${D}${FIXTURE_ROOT}/NOTICE
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@BINDIR@|${bindir}|g' \
            -e 's|@BASE_BINDIR@|${base_bindir}|g' \
            -e 's|@FIXTURE_ROOT@|${FIXTURE_ROOT}|g' \
            ${S}/${fixture_file} > ${D}${FIXTURE_ROOT}/${fixture_file}
        chmod 0644 ${D}${FIXTURE_ROOT}/${fixture_file}
    done
}

FILES:${PN} = "${bindir}/iotbench-maintenance-read ${sysconfdir}/sudoers.d/iotbench-maintenance ${FIXTURE_ROOT}"
