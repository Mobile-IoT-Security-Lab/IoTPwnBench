require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
require recipes-images/iotbench-java-command-fixture.inc

SUMMARY = "IoTBench corrected twin - ipcamera, CWE-77 Java app command injection"
IOTBENCH_CWE = "CWE-77"
IOTBENCH_VULN_INSTALL = "cwe077-java-app-command-injection-fixed"
DESCRIPTION = "Corrected twin of iotbench-ipcamera-cwe077-java-app-command-injection. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
