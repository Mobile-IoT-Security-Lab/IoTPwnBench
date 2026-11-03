require recipes-vulns/cwe787-native-buffer-overflow/cwe787-native-buffer-overflow_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-787 native buffer overflow"
DESCRIPTION = "Corrected twin of cwe787-native-buffer-overflow. A payload longer than the configuration is refused. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/*/test-guest.sh
}
