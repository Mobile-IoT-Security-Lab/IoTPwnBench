require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc
require recipes-images/iotbench-java-deserialization-fixture.inc

SUMMARY = "IoTBench fixture - smartbulb, CWE-502 Java deserialization"
IOTBENCH_CWE = "CWE-502"
IOTBENCH_VULN_INSTALL = "cwe502-java-deserialization"
