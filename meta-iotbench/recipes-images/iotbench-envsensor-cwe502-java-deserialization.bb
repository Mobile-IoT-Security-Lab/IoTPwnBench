require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc
require recipes-images/iotbench-java-deserialization-fixture.inc

SUMMARY = "IoTBench fixture - envsensor, CWE-502 Java deserialization"
IOTBENCH_CWE = "CWE-502"
IOTBENCH_VULN_INSTALL = "cwe502-java-deserialization"
