require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench target - smarthub, CWE-798 hardcoded credentials"
DESCRIPTION = "smarthub firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
