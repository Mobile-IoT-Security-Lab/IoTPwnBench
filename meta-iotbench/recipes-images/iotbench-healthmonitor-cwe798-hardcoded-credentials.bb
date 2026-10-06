require recipes-images/iotbench-image.inc
require recipes-devices/healthmonitor/device-healthmonitor.inc

SUMMARY = "IoTBench target - healthmonitor, CWE-798 hardcoded credentials"
DESCRIPTION = "healthmonitor firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
