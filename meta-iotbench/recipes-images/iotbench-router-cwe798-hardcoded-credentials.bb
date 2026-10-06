require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-798 hardcoded credentials"
DESCRIPTION = "router firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
