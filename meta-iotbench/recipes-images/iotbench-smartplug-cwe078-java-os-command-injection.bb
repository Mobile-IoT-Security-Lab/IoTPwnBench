require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc
require recipes-images/iotbench-java-command-fixture.inc

SUMMARY = "IoTBench fixture - smartplug, CWE-78 Java os command injection"
IOTBENCH_CWE = "CWE-78"
IOTBENCH_VULN_INSTALL = "cwe078-java-os-command-injection"
