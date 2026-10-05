SUMMARY = "IoTBench IP camera recording path traversal"
DESCRIPTION = "An unauthenticated camera recording-export CGI appends a user-controlled filename below its recording directory without canonicalization. Inspired by CVE-2016-15055; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ipcamera-recording.c file://clip-001.txt"
S = "${UNPACKDIR}"

RDEPENDS:${PN} = "device-ipcamera"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/ipcamera-recording.c -o ${B}/recording.cgi
}

do_install() {
    install -d ${D}/www/pages/cgi-bin
    install -m 0755 ${B}/recording.cgi ${D}/www/pages/cgi-bin/recording.cgi
    install -d ${D}${localstatedir}/lib/ipcamera/recordings
    install -m 0644 ${S}/clip-001.txt ${D}${localstatedir}/lib/ipcamera/recordings/clip-001.txt
}

FILES:${PN} = "/www/pages/cgi-bin/recording.cgi ${localstatedir}/lib/ipcamera/recordings"
