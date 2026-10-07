SUMMARY = "IoTBench fixture - CWE-798 hardcoding user passwords"
DESCRIPTION = "A local-only synthetic application account authenticates against a fixed plaintext password installed verbatim in every firmware. Local research only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
SRC_URI = "file://LICENSE file://accounts.conf file://iotbench-fixture-auth file://NOTICE file://ground-truth.json file://test-guest.sh"
S = "${UNPACKDIR}"
RDEPENDS:${PN} = "busybox"

do_install() {
    install -d ${D}${bindir} ${D}${sysconfdir}/iotbench/hardcoded-user-passwords ${D}${datadir}/iotbench/hardcoded-user-passwords
    # This is the actual local application account database, not a sample string.
    # No runtime provisioning or postinstall password generation is performed.
    install -m 0600 ${S}/accounts.conf ${D}${sysconfdir}/iotbench/hardcoded-user-passwords/accounts.conf
    sed -e 's|@SYSCONFDIR@|${sysconfdir}|g' ${S}/iotbench-fixture-auth > ${D}${bindir}/iotbench-fixture-auth
    chmod 0755 ${D}${bindir}/iotbench-fixture-auth
    install -m 0644 ${S}/NOTICE ${D}${datadir}/iotbench/hardcoded-user-passwords/NOTICE
    for fixture_file in ground-truth.json test-guest.sh; do
        sed -e 's|@SYSCONFDIR@|${sysconfdir}|g' -e 's|@BINDIR@|${bindir}|g' ${S}/$fixture_file > ${D}${datadir}/iotbench/hardcoded-user-passwords/$fixture_file
        chmod 0644 ${D}${datadir}/iotbench/hardcoded-user-passwords/$fixture_file
    done
}

FILES:${PN} = "${bindir}/iotbench-fixture-auth ${sysconfdir}/iotbench/hardcoded-user-passwords ${datadir}/iotbench/hardcoded-user-passwords"
CONFFILES:${PN} = "${sysconfdir}/iotbench/hardcoded-user-passwords/accounts.conf"
