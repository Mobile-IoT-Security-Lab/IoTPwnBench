require recipes-images/iotbench-image.inc
require recipes-devices/envsensor/device-envsensor.inc

SUMMARY = "IoTBench target - envsensor, CWE-327 weak 3DES cipher"
DESCRIPTION = "envsensor firmware with device backup encryption using obsolete Triple DES."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher"
