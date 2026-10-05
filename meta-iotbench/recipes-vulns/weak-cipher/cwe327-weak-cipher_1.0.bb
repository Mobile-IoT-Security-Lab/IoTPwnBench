SUMMARY = "IoTBench vulnerability module - CWE-327 Triple DES encryption"
DESCRIPTION = "Encrypts device backup data using obsolete 3DES-CBC with hardcoded encryption and HMAC keys and a fixed IV. Intentionally vulnerable; lab use only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE file://module.php file://iotbench-weak-cipher.c file://lighttpd-weak-cipher.conf"
S = "${UNPACKDIR}"

DEPENDS = "openssl"
RDEPENDS:${PN} = "router-dashboard"

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} ${S}/iotbench-weak-cipher.c ${LDFLAGS} -lcrypto -o ${B}/iotbench-weak-cipher
}

do_install() {
    install -d ${D}${bindir} ${D}${datadir}/router-dashboard/modules/weak-cipher
    install -m 0755 ${B}/iotbench-weak-cipher ${D}${bindir}/iotbench-weak-cipher
    install -m 0644 ${S}/module.php ${D}${datadir}/router-dashboard/modules/weak-cipher/module.php
    install -d ${D}${systemd_system_unitdir}/lighttpd.service.d
    install -m 0644 ${S}/lighttpd-weak-cipher.conf ${D}${systemd_system_unitdir}/lighttpd.service.d/weak-cipher.conf
}

FILES:${PN} = "${bindir}/iotbench-weak-cipher ${datadir}/router-dashboard/modules/weak-cipher ${systemd_system_unitdir}/lighttpd.service.d/weak-cipher.conf"
