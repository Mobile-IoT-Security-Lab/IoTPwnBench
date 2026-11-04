require recipes-vulns/weak-cipher/cwe327-weak-cipher_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-327 weak cipher"
DESCRIPTION = "Corrected twin of cwe327-weak-cipher. AES-256-CBC with a random IV and keys read from a root-only file, authenticated with HMAC-SHA256. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"
SRC_URI += "file://weak-cipher.key"

do_install:append() {
    # routerweb (uid/gid 995) only exists on the router device, so the key stays
    # root-owned and world-readable here rather than group-restricted to an
    # account that may not exist on every device.
    install -d -m 0755 ${D}${sysconfdir}/iotbench
    install -m 0644 ${S}/weak-cipher.key ${D}${sysconfdir}/iotbench/weak-cipher.key
}

FILES:${PN} += "${sysconfdir}/iotbench/weak-cipher.key"
