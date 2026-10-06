require recipes-images/iotbench-image.inc
require recipes-devices/smartplug/device-smartplug.inc

SUMMARY = "IoTBench target - smartplug, CWE-798 hardcoded credentials"
DESCRIPTION = "smartplug firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
