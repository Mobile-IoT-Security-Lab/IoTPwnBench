require recipes-vulns/cwe250-dangerous-suid-rights/cwe250-dangerous-suid-rights_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-250 dangerous SUID rights"
DESCRIPTION = "Corrected twin of cwe250-dangerous-suid-rights. The helper is installed with mode 0755 and no SUID bit. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    chmod 0755 ${D}${bindir}/iotbench-suid-fixture
}
