require recipes-vulns/cwe020-native-connection-string/cwe020-native-connection-string_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-20 native connection string"
DESCRIPTION = "Corrected twin of cwe020-native-connection-string. The cache field is restricted to private or shared. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/*/test-guest.sh
}
