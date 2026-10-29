require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc
require recipes-images/iotbench-java-deserialization-fixture.inc

SUMMARY = "IoTBench fixture - doorlock, CWE-502 Java deserialization"
IOTBENCH_CWE = "CWE-502"
IOTBENCH_VULN_INSTALL = "cwe502-java-deserialization"
