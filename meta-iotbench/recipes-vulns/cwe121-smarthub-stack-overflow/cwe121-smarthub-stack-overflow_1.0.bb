SUMMARY = "IoTBench smart hub database stack overflow"
DESCRIPTION = "A hub HTTP database endpoint copies an attacker-controlled bucket name into a fixed stack buffer. Inspired by CVE-2018-3915; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://smarthub-database.c"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "device-smarthub"

do_compile() {
    # Disable stack protector and FORTIFY so the intentional overflow is not
    # turned into __strcpy_chk, which would abort the process (SIGABRT -> HTTP
    # 500) instead of letting the controlled out-of-bounds write happen.
    ${CC} ${CFLAGS} ${LDFLAGS} -fno-stack-protector -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 ${S}/smarthub-database.c -o ${B}/hub-db.cgi
}

do_install() {
    install -d ${D}/www/pages/cgi-bin
    install -m 0755 ${B}/hub-db.cgi ${D}/www/pages/cgi-bin/hub-db.cgi
}

FILES:${PN} = "/www/pages/cgi-bin/hub-db.cgi"
