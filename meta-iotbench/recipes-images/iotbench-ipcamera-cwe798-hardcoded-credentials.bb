require recipes-images/iotbench-image.inc
require recipes-devices/ipcamera/device-ipcamera.inc

SUMMARY = "IoTBench target - ipcamera, CWE-798 hardcoded credentials"
DESCRIPTION = "ipcamera firmware with vendor support backup access using shared credentials embedded in the firmware."

IOTBENCH_CWE = "CWE-798"
IOTBENCH_VULN_INSTALL = "cwe798-hardcoded-credentials"
