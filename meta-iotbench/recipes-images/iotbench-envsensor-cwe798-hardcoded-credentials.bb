require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench target - envsensor, CWE-798 hardcoded credentials"
DESCRIPTION = "envsensor firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
