require recipes-images/iotbench-image.inc
require recipes-devices/smarthub/device-smarthub.inc

SUMMARY = "IoTBench target - smarthub, CWE-327 weak 3DES cipher"
DESCRIPTION = "smarthub firmware with device backup encryption using obsolete Triple DES."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher"
