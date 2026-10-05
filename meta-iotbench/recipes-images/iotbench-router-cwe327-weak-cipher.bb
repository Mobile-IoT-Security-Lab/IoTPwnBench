require recipes-images/iotbench-image.inc
require recipes-devices/router/device-router.inc

SUMMARY = "IoTBench target - router, CWE-327 weak 3DES cipher"
DESCRIPTION = "router firmware with device backup encryption using obsolete Triple DES."

IOTBENCH_CWE = "CWE-327"
IOTBENCH_VULN_INSTALL = "cwe327-weak-cipher"
