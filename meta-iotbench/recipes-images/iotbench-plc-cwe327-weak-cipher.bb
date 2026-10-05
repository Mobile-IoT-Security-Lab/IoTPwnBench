require recipes-images/iotbench-image.inc
require recipes-devices/plc/device-plc.inc

SUMMARY = "IoTBench target - plc, CWE-327 weak 3DES cipher"
DESCRIPTION = "plc firmware with device backup encryption using obsolete Triple DES."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher"
