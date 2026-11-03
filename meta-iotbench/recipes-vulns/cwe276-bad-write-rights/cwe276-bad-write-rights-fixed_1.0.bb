require recipes-vulns/cwe276-bad-write-rights/cwe276-bad-write-rights_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-276 bad write rights"
DESCRIPTION = "Corrected twin of cwe276-bad-write-rights. The bad directory is not group writable. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    chmod 0755 ${D}/srv/iotbench-ftp/bad
    rm -f ${D}${datadir}/iotbench/bad-write-rights/test-guest.py
}
