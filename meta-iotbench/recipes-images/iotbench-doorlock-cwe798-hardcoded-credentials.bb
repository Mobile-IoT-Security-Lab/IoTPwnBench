require recipes-images/iotbench-image.inc
require recipes-devices/doorlock/device-doorlock.inc

SUMMARY = "IoTBench target - doorlock, CWE-798 hardcoded credentials"
DESCRIPTION = "doorlock firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
