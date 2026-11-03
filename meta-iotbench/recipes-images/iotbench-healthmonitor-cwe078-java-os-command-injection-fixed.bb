require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc
require recipes-images/iotbench-java-command-fixture.inc

SUMMARY = "IoTBench corrected twin - healthmonitor, CWE-78 Java os command injection"
IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-java-os-command-injection-fixed"
DESCRIPTION = "Corrected twin of iotbench-healthmonitor-cwe078-java-os-command-injection. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
