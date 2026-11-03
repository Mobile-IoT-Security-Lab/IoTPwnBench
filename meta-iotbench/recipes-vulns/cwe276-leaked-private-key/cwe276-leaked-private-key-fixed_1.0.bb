require recipes-vulns/cwe276-leaked-private-key/cwe276-leaked-private-key_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-276 leaked private key"
DESCRIPTION = "Corrected twin of cwe276-leaked-private-key. The private key is readable only by root and is not served by the web server. No weakness is injected."

do_install() {
    install -d -m 0700 ${D}${sysconfdir}/ssl/private
    install -m 0600 ${S}/device-private.key ${D}${sysconfdir}/ssl/private/device-private.key
}

FILES:${PN} = "${sysconfdir}/ssl/private/device-private.key"
