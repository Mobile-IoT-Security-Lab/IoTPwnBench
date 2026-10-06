require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - plc, CWE-798 hardcoded credentials"
DESCRIPTION = "plc firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
