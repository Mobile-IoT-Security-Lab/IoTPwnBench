require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc
require recipes-images/iotbench-java-deserialization-fixture.inc

SUMMARY = "IoTBench corrected twin - router, CWE-502 Java deserialization"
IOTBENCH_CWE = "CWE-502"
IOTBENCH_VULN_INSTALL = "cwe502-java-deserialization-fixed"
DESCRIPTION = "Corrected twin of iotbench-router-cwe502-java-deserialization. The same device and service, with the weakness removed. No weakness is injected."
IOTBENCH_CORRECTS_CWE := "${IOTBENCH_CWE}"
IOTBENCH_CWE = "none"
