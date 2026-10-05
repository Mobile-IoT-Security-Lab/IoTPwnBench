SUMMARY = "IoTBench IP camera PTZ CGI command injection"
DESCRIPTION = "A camera PTZ CGI interpolates the preset query parameter into a shell command. Inspired by command-injection flaws in embedded camera CGI handlers; intentionally vulnerable for lab use."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=f5b1129dfbfc8afc083db247ff942d07"

SRC_URI = "file://LICENSE file://iotbench-camera-ptz.c"
S = "${UNPACKDIR}"

DEPENDS += "virtual/libc"
RDEPENDS:${PN} = "router-dashboard"

do_compile() {
    ${CC} ${CFLAGS} ${LDFLAGS} ${S}/iotbench-camera-ptz.c -o ${B}/ptz.cgi
}

do_install() {
    install -d ${D}/www/pages/cgi-bin
    install -m 0755 ${B}/ptz.cgi ${D}/www/pages/cgi-bin/ptz.cgi
}

FILES:${PN} = "/www/pages/cgi-bin/ptz.cgi"
