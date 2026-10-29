require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
require recipes-images/iotbench-java-command-fixture.inc

SUMMARY = "IoTBench fixture - ipcamera, CWE-77 Java app command injection"
IOTBENCH_CWE = "CWE-77"
IOTBENCH_VULN_INSTALL = "cwe077-java-app-command-injection"
