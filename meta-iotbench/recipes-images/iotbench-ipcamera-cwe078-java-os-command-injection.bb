require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc
require recipes-images/iotbench-java-command-fixture.inc

SUMMARY = "IoTBench fixture - ipcamera, CWE-78 Java os command injection"
IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-java-os-command-injection"
