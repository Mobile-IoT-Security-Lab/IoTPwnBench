require recipes-vulns/java-command-fixture/cwe077-java-app-command-injection_1.0.bb

SUMMARY = "IoTBench corrected variant - CWE-77 Java application command injection"
DESCRIPTION = "Corrected twin of cwe077-java-app-command-injection. The label is checked against its alphabet before it reaches the command. No weakness is injected."

# Files here replace the vulnerable ones of the same name.
FILESEXTRAPATHS:prepend := "${THISDIR}/files-fixed:"

do_install:append() {
    rm -f ${D}${datadir}/iotbench/java-command-fixture/test-java-command-fixture.py
}
