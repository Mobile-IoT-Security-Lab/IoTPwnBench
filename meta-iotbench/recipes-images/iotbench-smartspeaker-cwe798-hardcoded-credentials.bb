require recipes-images/iotbench-image.inc
require recipes-devices/smartspeaker/device-smartspeaker.inc

SUMMARY = "IoTBench target - smartspeaker, CWE-798 hardcoded credentials"
DESCRIPTION = "smartspeaker firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
