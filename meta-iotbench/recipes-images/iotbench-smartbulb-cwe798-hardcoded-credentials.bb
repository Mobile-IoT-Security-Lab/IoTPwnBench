require recipes-images/iotbench-image.inc
require recipes-devices/smartbulb/device-smartbulb.inc

SUMMARY = "IoTBench target - smartbulb, CWE-798 hardcoded credentials"
DESCRIPTION = "smartbulb firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
