require recipes-vulns/cwe502-java-deserialization/cwe502-java-deserialization_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-502 Java deserialization"
DESCRIPTION = "Corrected twin of cwe502-java-deserialization. Only the expected types are deserialized. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/java-deserialization-fixture/test-java-*.py
}
