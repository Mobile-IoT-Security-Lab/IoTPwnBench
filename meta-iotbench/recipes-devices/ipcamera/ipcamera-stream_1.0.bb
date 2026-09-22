SUMMARY = "IoTBench IP camera video skeleton (HTTP snapshot + MJPEG stream)"
DESCRIPTION = "Serves an HTTP JPEG snapshot and an MJPEG stream through the \
shared lighttpd, mimicking an IP camera video surface."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"

SRC_URI = "file://LICENSE \
           file://snapshot.jpg \
           file://stream.cgi"

S = "${UNPACKDIR}"

# Uses the shared web stack (lighttpd + cgi).
RDEPENDS:${PN} = "router-dashboard"

do_install() {
    install -d ${D}/www/pages
    install -m 0644 ${S}/snapshot.jpg ${D}/www/pages/snapshot.jpg
    install -m 0755 ${S}/stream.cgi ${D}/www/pages/stream.cgi
}

FILES:${PN} = "/www/pages/snapshot.jpg /www/pages/stream.cgi"
