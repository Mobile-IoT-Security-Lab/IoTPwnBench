require recipes-vulns/cwe120-service-buffer-overflow/cwe120-service-buffer-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-120 service buffer overflow"
DESCRIPTION = "Corrected twin of cwe120-service-buffer-overflow. A label that does not fit in the buffer is refused. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/*/test-service.py ${D}${datadir}/iotbench/*/test-guest.sh
}
